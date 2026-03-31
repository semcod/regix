"""Snapshot capture — collect metrics at a git ref."""

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
                         "coverage", "docstring_coverage", "quality_score", "imports"):
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

    For non-local refs, uses ``git worktree add`` to create a temporary
    checkout without modifying the original working tree.
    """
    from regix.backends import get_backend
    from regix.git import checkout_temporary, resolve_ref

    is_local = ref == "local"
    commit_sha: str | None = None

    if is_local:
        analysis_dir = workdir
    else:
        commit_sha = resolve_ref(ref, workdir)

    # Determine which backends to run
    if backend_names is None:
        backend_names = [v for v in config.backends.values() if v not in ("none", "builtin")]
        # Always include docstring (builtin)
        if "docstring" not in backend_names:
            backend_names.append("docstring")

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

    def _run_collection(target_dir: Path) -> list[SymbolMetrics]:
        files = _collect_files(target_dir, config.include, config.exclude)
        all_results: list[list[SymbolMetrics]] = []
        for bk in backends:
            try:
                result = bk.collect(target_dir, files, config)
                all_results.append(result)
            except Exception as exc:
                # Non-fatal: backend produces no output for this run
                all_results.append([])
        return _merge_symbols(all_results)

    if is_local:
        symbols = _run_collection(workdir)
    else:
        with checkout_temporary(ref, workdir) as tmp:
            symbols = _run_collection(tmp)

    return Snapshot(
        ref=ref,
        commit_sha=commit_sha,
        timestamp=datetime.now(timezone.utc),
        workdir=str(workdir),
        symbols=symbols,
        backend_versions=backend_versions,
    )
