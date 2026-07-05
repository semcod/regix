"""Tests for regix.cache — cache key, store, lookup, clear."""

from __future__ import annotations

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from regix.cache import (
    _cache_dir,
    _cache_key,
    clear,
    content_hash,
    load_file_index,
    lookup,
    save_file_index,
    split_cached_files,
    store,
    update_file_cache,
)
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


class TestContentHash:
    def test_deterministic(self):
        assert content_hash("x = 1") == content_hash("x = 1")

    def test_changes_with_content(self):
        assert content_hash("x = 1") != content_hash("x = 2")


class TestFileIndex:
    def test_load_missing_returns_empty(self, tmp_path: Path):
        assert load_file_index(cache_dir=str(tmp_path)) == {}

    def test_save_then_load_roundtrips(self, tmp_path: Path):
        save_file_index({"a.py": {"hash": "abc"}}, cache_dir=str(tmp_path))
        assert load_file_index(cache_dir=str(tmp_path)) == {"a.py": {"hash": "abc"}}

    def test_load_corrupted_returns_empty(self, tmp_path: Path):
        path = tmp_path / "file_index.json.gz"
        path.write_bytes(b"not valid gzip")
        assert load_file_index(cache_dir=str(tmp_path)) == {}


class TestSplitCachedFiles:
    def test_unindexed_file_needs_analysis(self, tmp_path: Path):
        files = [Path("a.py")]
        sources = {"a.py": "x = 1"}
        to_analyze, cached = split_cached_files(
            files, sources, {"lizard": "1.0"}, cache_dir=str(tmp_path)
        )
        assert to_analyze == files
        assert cached == []

    def test_unchanged_file_is_served_from_cache(self, tmp_path: Path):
        files = [Path("a.py")]
        sources = {"a.py": "x = 1"}
        versions = {"lizard": "1.0"}
        symbols = [SymbolMetrics(file="a.py", symbol="f", cc=3)]

        update_file_cache(files, sources, symbols, versions, cache_dir=str(tmp_path))
        to_analyze, cached = split_cached_files(
            files, sources, versions, cache_dir=str(tmp_path)
        )

        assert to_analyze == []
        assert len(cached) == 1
        assert cached[0].cc == 3

    def test_changed_content_invalidates_cache_entry(self, tmp_path: Path):
        files = [Path("a.py")]
        versions = {"lizard": "1.0"}
        symbols = [SymbolMetrics(file="a.py", symbol="f", cc=3)]

        update_file_cache(
            files, {"a.py": "x = 1"}, symbols, versions, cache_dir=str(tmp_path)
        )
        to_analyze, cached = split_cached_files(
            files, {"a.py": "x = 2"}, versions, cache_dir=str(tmp_path)
        )

        assert to_analyze == files
        assert cached == []

    def test_changed_backend_version_invalidates_cache_entry(self, tmp_path: Path):
        files = [Path("a.py")]
        sources = {"a.py": "x = 1"}
        symbols = [SymbolMetrics(file="a.py", symbol="f", cc=3)]

        update_file_cache(
            files, sources, symbols, {"lizard": "1.0"}, cache_dir=str(tmp_path)
        )
        to_analyze, cached = split_cached_files(
            files, sources, {"lizard": "2.0"}, cache_dir=str(tmp_path)
        )

        assert to_analyze == files
        assert cached == []

    def test_mixed_changed_and_unchanged_files(self, tmp_path: Path):
        files = [Path("a.py"), Path("b.py")]
        sources = {"a.py": "x = 1", "b.py": "y = 2"}
        versions = {"lizard": "1.0"}
        symbols = [
            SymbolMetrics(file="a.py", symbol="f", cc=1),
            SymbolMetrics(file="b.py", symbol="g", cc=2),
        ]
        update_file_cache(files, sources, symbols, versions, cache_dir=str(tmp_path))

        changed_sources = {"a.py": "x = 1", "b.py": "y = 999"}  # only b.py changed
        to_analyze, cached = split_cached_files(
            files, changed_sources, versions, cache_dir=str(tmp_path)
        )

        assert to_analyze == [Path("b.py")]
        assert len(cached) == 1
        assert cached[0].file == "a.py"


class TestUpdateFileCache:
    def test_writes_entry_retrievable_via_index(self, tmp_path: Path):
        files = [Path("a.py")]
        sources = {"a.py": "x = 1"}
        symbols = [SymbolMetrics(file="a.py", symbol="f", cc=3, mi=50.0)]

        update_file_cache(
            files, sources, symbols, {"lizard": "1.0"}, cache_dir=str(tmp_path)
        )

        index = load_file_index(cache_dir=str(tmp_path))
        assert index["a.py"]["hash"] == content_hash("x = 1")
        assert index["a.py"]["symbols"][0]["cc"] == 3
        assert index["a.py"]["symbols"][0]["mi"] == 50.0

    def test_file_with_no_symbols_still_cached_as_empty(self, tmp_path: Path):
        """A file that produced zero symbols this run must still be recorded
        as a cache hit next time -- otherwise an empty-result file would be
        re-analyzed on every single run forever."""
        files = [Path("empty.py")]
        sources = {"empty.py": ""}

        update_file_cache(
            files, sources, [], {"lizard": "1.0"}, cache_dir=str(tmp_path)
        )
        to_analyze, cached = split_cached_files(
            files, sources, {"lizard": "1.0"}, cache_dir=str(tmp_path)
        )

        assert to_analyze == []
        assert cached == []
