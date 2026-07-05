"""Snapshot capture — collect metrics at a git ref.

All analysis is performed **in RAM** — file contents are read once
(via ``git archive`` for committed refs, or a single pass over the
working tree for ``local``) and passed to backends as a
``dict[str, str]`` (relative_path → source_text).  No temporary
worktrees are created on disk.
"""

from __future__ import annotations

import fnmatch
from datetime import datetime, timezone
from pathlib import Path

from regix.config import RegressionConfig
from regix.models import Snapshot, SymbolMetrics


def _should_ignore_dir(dirname: str) -> bool:
    """Check if directory should be ignored during traversal."""
    ignored_dirs = {
        "node_modules", ".venv", ".git", "project", "redeploy", "reports",
        "__pycache__", ".vscode", ".idea", ".windsurf", ".cursor", ".aider", ".claude",
        "archive", "_archive", "tests", "generated", "dist", "build", ".wup", ".planfile"
    }
    return (
        dirname in ignored_dirs
        or dirname.startswith("batch_")
        or dirname.startswith(".")
    )

def _apply_include_patterns(files: list[Path], include: list[str]) -> list[Path]:
    """Apply include patterns to file list."""
    if not include:
        return files
    matched: list[Path] = []
    for pattern in include:
        matched.extend(f for f in files if fnmatch.fnmatch(str(f), pattern))
    return list(dict.fromkeys(matched))  # dedupe, preserve order

def _apply_exclude_patterns(files: list[Path], exclude: list[str]) -> list[Path]:
    """Apply exclude patterns to file list."""
    filtered: list[Path] = []
    for f in files:
        skip = False
        for pattern in exclude:
            if fnmatch.fnmatch(str(f), pattern):
                skip = True
                break
        if not skip:
            filtered.append(f)
    return filtered

def _collect_files(
    workdir: Path,
    include: list[str],
    exclude: list[str],
) -> list[Path]:
    """Collect Python files matching include/exclude patterns, pruning ignored directories during traversal."""
    import os
    all_py = []
    
    for root, dirs, files in os.walk(workdir, topdown=True):
        dirs[:] = [d for d in dirs if not _should_ignore_dir(d)]
        
        for file in files:
            if file.endswith(".py"):
                all_py.append(Path(root) / file)
                
    relative = [f.relative_to(workdir) for f in sorted(all_py)]
    relative = _apply_include_patterns(relative, include)
    relative = _apply_exclude_patterns(relative, exclude)

    return relative


def _filter_sources(
    sources: dict[str, str],
    include: list[str],
    exclude: list[str],
) -> tuple[list[Path], dict[str, str]]:
    """Apply include/exclude patterns to an in-memory sources dict.

    Returns (file_list, filtered_sources) where both contain only the
    matching paths.
    """
    keys = sorted(sources.keys())

    if include:
        matched: list[str] = []
        for pattern in include:
            matched.extend(k for k in keys if fnmatch.fnmatch(k, pattern))
        keys = list(dict.fromkeys(matched))

    filtered: list[str] = []
    for k in keys:
        skip = False
        for pattern in exclude:
            if fnmatch.fnmatch(k, pattern):
                skip = True
                break
        if not skip:
            filtered.append(k)

    files = [Path(k) for k in filtered]
    src = {k: sources[k] for k in filtered}
    return files, src


def _merge_symbols(
    all_results: list[list[SymbolMetrics]],
) -> list[SymbolMetrics]:
    """Merge symbol metrics from multiple backends.

    When multiple backends report on the same (file, symbol), merge their
    non-None fields into a single SymbolMetrics object.
    """
    index: dict[tuple[str, str | None], SymbolMetrics] = {}
    for result_list in all_results:
        for sm in result_list:
            key = (sm.file, sm.symbol)
            if key not in index:
                index[key] = SymbolMetrics(file=sm.file, symbol=sm.symbol, raw={})
            existing = index[key]
            # Merge fields: keep first non-None value
            for attr in (
                "line_start",
                "line_end",
                "cc",
                "mi",
                "length",
                "coverage",
                "docstring_coverage",
                "quality_score",
                "imports",
                "fan_out",
                "call_count",
                "symbol_count",
                "param_count",
                "node_type_diversity",
                "logic_density",
            ):
                new_val = getattr(sm, attr)
                if new_val is not None and getattr(existing, attr) is None:
                    setattr(existing, attr, new_val)
            # Merge raw dicts
            existing.raw.update(sm.raw)

    return list(index.values())


def _resolve_backends(
    backend_names: list[str] | None, config: RegressionConfig
) -> tuple[list, dict[str, str]]:
    """Return (backend_instances, versions_dict)."""
    from regix.backends import get_backend

    if backend_names is None:
        backend_names = [
            v for v in config.backends.values() if v not in ("none", "builtin")
        ]
        for builtin in ("docstring", "structure", "architecture"):
            if builtin not in backend_names:
                backend_names.append(builtin)

    backends = []
    for name in backend_names:
        if name in ("none", ""):
            continue
        bk = get_backend(name)
        if bk is None or not bk.is_available():
            continue
        backends.append(bk)

    versions = {bk.name: bk.version() for bk in backends}
    return backends, versions


def _load_sources(
    ref: str, workdir: Path, config: RegressionConfig, is_local: bool
) -> tuple[list[Path], dict[str, str]]:
    """Load source files into RAM and return (file_list, sources_dict)."""
    from regix.git import read_local_sources, read_tree_sources

    if is_local:
        disk_files = _collect_files(workdir, config.include, config.exclude)
        sources = read_local_sources(workdir, disk_files)
        files = [Path(k) for k in sources]
        return files, sources

    raw_sources = read_tree_sources(ref, workdir, suffix=".py")
    return _filter_sources(raw_sources, config.include, config.exclude)


def _run_backends(
    backends: list,
    workdir: Path,
    files: list[Path],
    config: RegressionConfig,
    sources: dict[str, str],
) -> list[list[SymbolMetrics]]:
    """Run each backend and collect results, tolerating backend failures."""
    all_results: list[list[SymbolMetrics]] = []
    for bk in backends:
        try:
            all_results.append(bk.collect(workdir, files, config, sources=sources))
        except Exception:
            all_results.append([])
    return all_results


def capture(
    ref: str,
    workdir: Path,
    config: RegressionConfig,
    backend_names: list[str] | None = None,
    restrict_to_files: list[str] | None = None,
    use_file_cache: bool = False,
    file_cache_dir: str = "~/.cache/regix",
) -> Snapshot:
    """Capture a snapshot at a git ref or the local working tree.

    All file contents are loaded into RAM first — no temporary worktrees
    are created.  For committed refs ``git archive`` streams the tree
    directly into memory; for ``local`` the working tree is read once.

    ``use_file_cache`` skips backend analysis for any file whose content
    hash + backend-versions fingerprint already has a cached result,
    regardless of *ref* — unlike the commit-sha-keyed whole-snapshot cache
    in :mod:`regix.cache`, this also speeds up ``local`` and a moving
    ``HEAD`` where only a handful of files actually changed since the last
    check.
    """
    from regix.git import resolve_ref

    is_local = ref == "local"
    commit_sha: str | None = None
    if not is_local:
        commit_sha = resolve_ref(ref, workdir)

    backends, backend_versions = _resolve_backends(backend_names, config)
    files, sources = _load_sources(ref, workdir, config, is_local)

    # Filter by restrict_to_files if provided
    if restrict_to_files is not None:
        restrict_set = {str(Path(f)) for f in restrict_to_files}
        files = [f for f in files if str(f) in restrict_set]
        sources = {k: v for k, v in sources.items() if k in restrict_set}

    if use_file_cache:
        from regix.cache import split_cached_files, update_file_cache

        files_to_analyze, cached_symbols = split_cached_files(
            files, sources, backend_versions, cache_dir=file_cache_dir
        )
        all_results = _run_backends(
            backends, workdir, files_to_analyze, config, sources
        )
        fresh_symbols = _merge_symbols(all_results)
        update_file_cache(
            files_to_analyze,
            sources,
            fresh_symbols,
            backend_versions,
            cache_dir=file_cache_dir,
        )
        symbols = cached_symbols + fresh_symbols
    else:
        all_results = _run_backends(backends, workdir, files, config, sources)
        symbols = _merge_symbols(all_results)

    return Snapshot(
        ref=ref,
        commit_sha=commit_sha,
        timestamp=datetime.now(timezone.utc),
        workdir=str(workdir),
        symbols=symbols,
        backend_versions=backend_versions,
    )
