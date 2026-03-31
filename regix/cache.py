"""Content-addressed snapshot cache."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from regix.models import Snapshot


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
    data = json.dumps({
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
    }, default=str)
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
