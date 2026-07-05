"""Content-addressed snapshot cache."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from regix.models import Snapshot, SymbolMetrics


def _cache_dir(config_dir: str = "~/.cache/regix") -> Path:
    """Resolve cache directory (XDG-compliant)."""
    import os

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        d = Path(xdg) / "regix"
    else:
        d = Path(config_dir).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(commit_sha: str, backend_versions: dict[str, str]) -> str:
    """Compute cache key from commit SHA and backend versions."""
    raw = f"{commit_sha}:{json.dumps(sorted(backend_versions.items()))}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def lookup(
    commit_sha: str,
    backend_versions: dict[str, str],
    cache_dir: str = "~/.cache/regix",
) -> Snapshot | None:
    """Return cached snapshot or None."""
    d = _cache_dir(cache_dir)
    key = _cache_key(commit_sha, backend_versions)
    path = d / f"{key}.json.gz"
    if not path.exists():
        return None
    try:
        raw = gzip.decompress(path.read_bytes()).decode("utf-8")
        data = json.loads(raw)
        from datetime import datetime
        from regix.models import SymbolMetrics

        symbols = [SymbolMetrics(**s) for s in data.get("symbols", [])]
        return Snapshot(
            ref=data["ref"],
            commit_sha=data["commit_sha"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            workdir=data.get("workdir", "."),
            backend_versions=data.get("backend_versions", {}),
            symbols=symbols,
        )
    except Exception:
        return None


def store(
    snapshot: Snapshot,
    cache_dir: str = "~/.cache/regix",
) -> Path:
    """Store a snapshot in the cache, return its path."""
    d = _cache_dir(cache_dir)
    if not snapshot.commit_sha:
        raise ValueError("Cannot cache a snapshot without a commit SHA (local ref)")
    key = _cache_key(snapshot.commit_sha, snapshot.backend_versions)
    path = d / f"{key}.json.gz"
    data = json.dumps(
        {
            "ref": snapshot.ref,
            "commit_sha": snapshot.commit_sha,
            "timestamp": snapshot.timestamp.isoformat(),
            "workdir": str(snapshot.workdir),
            "backend_versions": snapshot.backend_versions,
            "symbols": [
                {
                    "file": s.file,
                    "symbol": s.symbol,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "cc": s.cc,
                    "mi": s.mi,
                    "length": s.length,
                    "coverage": s.coverage,
                    "docstring_coverage": s.docstring_coverage,
                    "quality_score": s.quality_score,
                    "imports": s.imports,
                    "raw": s.raw,
                }
                for s in snapshot.symbols
            ],
        },
        default=str,
    )
    path.write_bytes(gzip.compress(data.encode("utf-8")))
    return path


def clear(cache_dir: str = "~/.cache/regix") -> int:
    """Remove all cached snapshots. Returns count removed."""
    d = _cache_dir(cache_dir)
    count = 0
    for f in d.glob("*.json.gz"):
        f.unlink()
        count += 1
    return count


# --- Per-file incremental cache ---------------------------------------
#
# The commit-sha-keyed cache above only helps for a *fixed* ref (a tag or
# already-analyzed commit) -- it's unusable for `ref="local"` (snapshots
# there never get a commit_sha) and gets fully invalidated by every new
# commit on a moving ref like HEAD, even when only one file actually
# changed. This is exactly the case paid on every koru loop iteration and
# every manual `regix gates` check during active development. This second
# cache is keyed per-file by content hash + backend versions instead, so
# unchanged files are never re-analyzed regardless of which ref/commit
# they came from.

_FILE_INDEX_NAME = "file_index.json.gz"


def content_hash(source: str) -> str:
    """Stable content hash used as the per-file cache key component."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _file_index_path(cache_dir: str) -> Path:
    return _cache_dir(cache_dir) / _FILE_INDEX_NAME


def _versions_key(backend_versions: dict[str, str]) -> str:
    return json.dumps(sorted(backend_versions.items()))


def load_file_index(cache_dir: str = "~/.cache/regix") -> dict:
    """Load the per-file cache index, or an empty dict if absent/corrupt."""
    path = _file_index_path(cache_dir)
    if not path.exists():
        return {}
    try:
        raw = gzip.decompress(path.read_bytes()).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return {}


def save_file_index(index: dict, cache_dir: str = "~/.cache/regix") -> None:
    """Persist the per-file cache index."""
    path = _file_index_path(cache_dir)
    data = json.dumps(index, default=str)
    path.write_bytes(gzip.compress(data.encode("utf-8")))


def split_cached_files(
    files: list[Path],
    sources: dict[str, str],
    backend_versions: dict[str, str],
    cache_dir: str = "~/.cache/regix",
    index: dict | None = None,
) -> tuple[list[Path], list[SymbolMetrics]]:
    """Split *files* into (files needing analysis, symbols already cached).

    A file is a cache hit only when both its content hash *and* the
    backend-versions fingerprint match the cached entry -- an upgraded
    lizard/radon/etc. invalidates every entry rather than serving stale
    metrics silently.
    """
    if index is None:
        index = load_file_index(cache_dir)
    versions = _versions_key(backend_versions)

    to_analyze: list[Path] = []
    cached_symbols: list[SymbolMetrics] = []
    for f in files:
        key = str(f)
        source = sources.get(key)
        if source is None:
            to_analyze.append(f)
            continue

        entry = index.get(key)
        h = content_hash(source)
        if entry and entry.get("hash") == h and entry.get("versions") == versions:
            cached_symbols.extend(SymbolMetrics(**s) for s in entry.get("symbols", []))
        else:
            to_analyze.append(f)

    return to_analyze, cached_symbols


def update_file_cache(
    files: list[Path],
    sources: dict[str, str],
    fresh_symbols: list[SymbolMetrics],
    backend_versions: dict[str, str],
    cache_dir: str = "~/.cache/regix",
) -> None:
    """Record freshly computed symbols for *files* in the per-file cache.

    *fresh_symbols* may span multiple files (backends emit one flat list);
    grouped by `.file` here before writing each file's cache entry.
    """
    index = load_file_index(cache_dir)
    versions = _versions_key(backend_versions)

    by_file: dict[str, list[SymbolMetrics]] = {}
    for sm in fresh_symbols:
        by_file.setdefault(sm.file, []).append(sm)

    for f in files:
        key = str(f)
        source = sources.get(key)
        if source is None:
            continue
        index[key] = {
            "hash": content_hash(source),
            "versions": versions,
            "symbols": [asdict(sm) for sm in by_file.get(key, [])],
        }

    save_file_index(index, cache_dir)
