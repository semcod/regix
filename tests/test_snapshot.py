"""Tests for regix.snapshot — file collection, filtering, symbol merging, capture."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from regix.config import RegressionConfig
from regix.models import SymbolMetrics
from regix.snapshot import _collect_files, _filter_sources, _merge_symbols, capture


class TestCollectFiles:
    def test_collects_py_files(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        (tmp_path / "c.txt").write_text("not python")
        result = _collect_files(tmp_path, include=[], exclude=[])
        names = [str(f) for f in result]
        assert "a.py" in names
        assert "b.py" in names
        assert "c.txt" not in names

    def test_exclude_pattern(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("x = 1")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("x = 1")
        result = _collect_files(tmp_path, include=[], exclude=["tests/**"])
        names = [str(f) for f in result]
        assert any("main.py" in n for n in names)
        assert not any("test_main" in n for n in names)

    def test_include_pattern(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")
        result = _collect_files(tmp_path, include=["a.py"], exclude=[])
        names = [str(f) for f in result]
        assert "a.py" in names
        assert "b.py" not in names


class TestFilterSources:
    def test_basic_filter(self):
        sources = {"a.py": "x=1", "b.py": "y=2", "tests/c.py": "z=3"}
        files, filtered = _filter_sources(sources, include=[], exclude=["tests/**"])
        assert len(files) == 2
        assert "tests/c.py" not in filtered

    def test_include_filter(self):
        sources = {"a.py": "x=1", "b.py": "y=2"}
        files, filtered = _filter_sources(sources, include=["a.py"], exclude=[])
        assert len(files) == 1
        assert "a.py" in filtered

    def test_no_filters(self):
        sources = {"a.py": "x=1", "b.py": "y=2"}
        files, filtered = _filter_sources(sources, include=[], exclude=[])
        assert len(files) == 2


class TestMergeSymbols:
    def test_merge_same_symbol(self):
        r1 = [SymbolMetrics(file="a.py", symbol="func", cc=5)]
        r2 = [SymbolMetrics(file="a.py", symbol="func", mi=30.0)]
        merged = _merge_symbols([r1, r2])
        assert len(merged) == 1
        assert merged[0].cc == 5
        assert merged[0].mi == 30.0

    def test_merge_different_symbols(self):
        r1 = [SymbolMetrics(file="a.py", symbol="f1", cc=5)]
        r2 = [SymbolMetrics(file="a.py", symbol="f2", cc=3)]
        merged = _merge_symbols([r1, r2])
        assert len(merged) == 2

    def test_first_value_wins(self):
        r1 = [SymbolMetrics(file="a.py", symbol="func", cc=5)]
        r2 = [SymbolMetrics(file="a.py", symbol="func", cc=10)]
        merged = _merge_symbols([r1, r2])
        assert merged[0].cc == 5  # first non-None wins

    def test_merge_raw_dicts(self):
        r1 = [SymbolMetrics(file="a.py", symbol="func", raw={"a": 1})]
        r2 = [SymbolMetrics(file="a.py", symbol="func", raw={"b": 2})]
        merged = _merge_symbols([r1, r2])
        assert merged[0].raw == {"a": 1, "b": 2}

    def test_empty_input(self):
        merged = _merge_symbols([])
        assert merged == []

    def test_module_level_symbol(self):
        r1 = [SymbolMetrics(file="a.py", symbol=None, cc=2)]
        merged = _merge_symbols([r1])
        assert len(merged) == 1
        assert merged[0].symbol is None


class TestCapture:
    @patch("regix.backends.get_backend")
    @patch("regix.git.read_local_sources")
    def test_capture_local(self, mock_read, mock_get_bk, tmp_path: Path):
        (tmp_path / "a.py").write_text("x = 1")
        mock_read.return_value = {"a.py": "x = 1"}

        mock_bk = MagicMock()
        mock_bk.name = "structure"
        mock_bk.version.return_value = "1.0"
        mock_bk.is_available.return_value = True
        mock_bk.collect.return_value = [
            SymbolMetrics(file="a.py", symbol=None, cc=2),
        ]
        mock_get_bk.return_value = mock_bk

        cfg = RegressionConfig()
        snap = capture("local", tmp_path, cfg, backend_names=["structure"])
        assert snap.ref == "local"
        assert snap.commit_sha is None
        assert len(snap.symbols) >= 1

    @patch("regix.backends.get_backend")
    @patch("regix.git.read_tree_sources")
    @patch("regix.git.resolve_ref", return_value="abc123")
    def test_capture_ref(self, mock_resolve, mock_read_tree, mock_get_bk, tmp_path: Path):
        mock_read_tree.return_value = {"a.py": "x = 1"}

        mock_bk = MagicMock()
        mock_bk.name = "structure"
        mock_bk.version.return_value = "1.0"
        mock_bk.is_available.return_value = True
        mock_bk.collect.return_value = [
            SymbolMetrics(file="a.py", symbol="f", cc=5),
        ]
        mock_get_bk.return_value = mock_bk

        cfg = RegressionConfig()
        snap = capture("HEAD", tmp_path, cfg, backend_names=["structure"])
        assert snap.ref == "HEAD"
        assert snap.commit_sha == "abc123"
        assert len(snap.symbols) >= 1

    @patch("regix.backends.get_backend")
    @patch("regix.git.read_local_sources")
    def test_capture_backend_error_handled(self, mock_read, mock_get_bk, tmp_path: Path):
        (tmp_path / "a.py").write_text("x = 1")
        mock_read.return_value = {"a.py": "x = 1"}

        mock_bk = MagicMock()
        mock_bk.name = "bad"
        mock_bk.version.return_value = "0.0"
        mock_bk.is_available.return_value = True
        mock_bk.collect.side_effect = RuntimeError("boom")
        mock_get_bk.return_value = mock_bk

        cfg = RegressionConfig()
        snap = capture("local", tmp_path, cfg, backend_names=["bad"])
        assert snap.ref == "local"

    @patch("regix.backends.get_backend")
    @patch("regix.git.read_local_sources")
    def test_capture_unavailable_backend_skipped(self, mock_read, mock_get_bk, tmp_path: Path):
        (tmp_path / "a.py").write_text("x = 1")
        mock_read.return_value = {"a.py": "x = 1"}

        mock_bk = MagicMock()
        mock_bk.name = "missing"
        mock_bk.is_available.return_value = False
        mock_get_bk.return_value = mock_bk

        cfg = RegressionConfig()
        snap = capture("local", tmp_path, cfg, backend_names=["missing"])
        assert len(snap.symbols) == 0

    @patch("regix.backends.get_backend", return_value=None)
    @patch("regix.git.read_local_sources")
    def test_capture_unknown_backend_skipped(self, mock_read, mock_get_bk, tmp_path: Path):
        (tmp_path / "a.py").write_text("x = 1")
        mock_read.return_value = {"a.py": "x = 1"}

        cfg = RegressionConfig()
        snap = capture("local", tmp_path, cfg, backend_names=["nonexistent"])
        assert len(snap.symbols) == 0
