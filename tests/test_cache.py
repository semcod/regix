"""Tests for regix.cache — cache key, store, lookup, clear."""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from regix.cache import _cache_dir, _cache_key, clear, lookup, store
from regix.models import Snapshot, SymbolMetrics


class TestCacheKey:
    def test_deterministic(self):
        k1 = _cache_key("abc123", {"lizard": "1.0"})
        k2 = _cache_key("abc123", {"lizard": "1.0"})
        assert k1 == k2

    def test_different_sha(self):
        k1 = _cache_key("abc123", {"lizard": "1.0"})
        k2 = _cache_key("def456", {"lizard": "1.0"})
        assert k1 != k2

    def test_different_versions(self):
        k1 = _cache_key("abc123", {"lizard": "1.0"})
        k2 = _cache_key("abc123", {"lizard": "2.0"})
        assert k1 != k2

    def test_length(self):
        k = _cache_key("abc", {})
        assert len(k) == 24


class TestCacheDir:
    def test_default_creates_dir(self, tmp_path: Path):
        d = _cache_dir(str(tmp_path / "cache" / "regix"))
        assert d.exists()
        assert d.is_dir()

    def test_xdg_override(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
        d = _cache_dir()
        assert "xdg" in str(d)
        assert d.name == "regix"
        assert d.exists()


def _make_snapshot(**overrides) -> Snapshot:
    defaults = dict(
        ref="HEAD",
        commit_sha="abc1234567890",
        timestamp=datetime.now(timezone.utc),
        workdir=".",
        symbols=[SymbolMetrics(file="a.py", symbol="func", cc=3, mi=40.0)],
        backend_versions={"lizard": "1.0"},
    )
    defaults.update(overrides)
    return Snapshot(**defaults)


class TestStore:
    def test_store_creates_file(self, tmp_path: Path):
        snap = _make_snapshot()
        path = store(snap, cache_dir=str(tmp_path))
        assert path.exists()
        assert path.suffix == ".gz"

    def test_stored_file_is_gzipped_json(self, tmp_path: Path):
        snap = _make_snapshot()
        path = store(snap, cache_dir=str(tmp_path))
        raw = gzip.decompress(path.read_bytes()).decode("utf-8")
        data = json.loads(raw)
        assert data["commit_sha"] == "abc1234567890"
        assert len(data["symbols"]) == 1

    def test_store_raises_without_sha(self, tmp_path: Path):
        snap = _make_snapshot(commit_sha=None)
        with pytest.raises(ValueError, match="commit SHA"):
            store(snap, cache_dir=str(tmp_path))


class TestLookup:
    def test_lookup_miss(self, tmp_path: Path):
        result = lookup("abc123", {"lizard": "1.0"}, cache_dir=str(tmp_path))
        assert result is None

    def test_lookup_corrupted_file(self, tmp_path: Path):
        snap = _make_snapshot()
        path = store(snap, cache_dir=str(tmp_path))
        # Corrupt the file
        path.write_bytes(b"not valid gzip")
        result = lookup(
            snap.commit_sha, snap.backend_versions,
            cache_dir=str(tmp_path),
        )
        assert result is None

    def test_lookup_after_store_finds_file(self, tmp_path: Path):
        snap = _make_snapshot()
        store(snap, cache_dir=str(tmp_path))
        # lookup finds the file and returns something (not None)
        result = lookup(
            snap.commit_sha, snap.backend_versions,
            cache_dir=str(tmp_path),
        )
        assert result is not None


class TestClear:
    def test_clear_removes_files(self, tmp_path: Path):
        snap = _make_snapshot()
        store(snap, cache_dir=str(tmp_path))
        count = clear(cache_dir=str(tmp_path))
        assert count >= 1
        assert list(tmp_path.glob("*.json.gz")) == []

    def test_clear_empty_dir(self, tmp_path: Path):
        count = clear(cache_dir=str(tmp_path))
        assert count == 0
