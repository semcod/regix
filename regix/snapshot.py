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
from regix.exceptions import BackendError
from regix.models import Snapshot, SymbolMetrics


def _collect_files(
    workdir: Path,
    include: list[str],
    exclude: list[str],
) -> list[Path]:
    """Collect Python files matching include/exclude patterns."""
    # Default: all .py files
    all_py = sorted(workdir.rglob("*.py"))
    relative = [f.relative_to(workdir) for f in all_py]

    if include:
        matched: list[Path] = []
        for pattern in include:
            matched.extend(f for f in relative if fnmatch.fnmatch(str(f), pattern))
        relative = list(dict.fromkeys(matched))  # dedupe, preserve order

    filtered: list[Path] = []
    for f in relative:
        skip = False
        for pattern in exclude:
            if fnmatch.fnmatch(str(f), pattern):
                skip = True
                break
        if not skip:
            filtered.append(f)

    return filtered


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
            for attr in ("line_start", "line_end", "cc", "mi", "length",
                         "coverage", "docstring_coverage", "quality_score", "imports",
                         "fan_out", "call_count", "symbol_count",
                         "param_count", "node_type_diversity", "logic_density"):
                new_val = getattr(sm, attr)
                if new_val is not None and getattr(existing, attr) is None:
                    setattr(existing, attr, new_val)
            # Merge raw dicts
            existing.raw.update(sm.raw)

    return list(index.values())


def capture(
    ref: str,
    workdir: Path,
    config: RegressionConfig,
    backend_names: list[str] | None = None,
) -> Snapshot:
    """Capture a snapshot at a git ref or the local working tree.

    All file contents are loaded into RAM first — no temporary worktrees
    are created.  For committed refs ``git archive`` streams the tree
    directly into memory; for ``local`` the working tree is read once.
    """
    from regix.backends import get_backend
    from regix.git import read_local_sources, read_tree_sources, resolve_ref

    is_local = ref == "local"
    commit_sha: str | None = None

    if not is_local:
        commit_sha = resolve_ref(ref, workdir)

    # Determine which backends to run
    if backend_names is None:
        backend_names = [v for v in config.backends.values() if v not in ("none", "builtin")]
        # Always include builtin backends
        if "docstring" not in backend_names:
            backend_names.append("docstring")
        if "structure" not in backend_names:
            backend_names.append("structure")
        if "architecture" not in backend_names:
            backend_names.append("architecture")

    backends = []
    for name in backend_names:
        if name in ("none", ""):
            continue
        bk = get_backend(name)
        if bk is None:
            continue
        if not bk.is_available():
            continue
        backends.append(bk)

    backend_versions = {bk.name: bk.version() for bk in backends}

    # ── Load all sources into RAM ──────────────────────────────────────────
    if is_local:
        disk_files = _collect_files(workdir, config.include, config.exclude)
        sources = read_local_sources(workdir, disk_files)
        files = [Path(k) for k in sources]
    else:
        raw_sources = read_tree_sources(ref, workdir, suffix=".py")
        files, sources = _filter_sources(raw_sources, config.include, config.exclude)

    # ── Run backends with in-memory sources ────────────────────────────────
    all_results: list[list[SymbolMetrics]] = []
    for bk in backends:
        try:
            result = bk.collect(workdir, files, config, sources=sources)
            all_results.append(result)
        except Exception:
            all_results.append([])
    symbols = _merge_symbols(all_results)

    return Snapshot(
        ref=ref,
        commit_sha=commit_sha,
        timestamp=datetime.now(timezone.utc),
        workdir=str(workdir),
        symbols=symbols,
        backend_versions=backend_versions,
    )
