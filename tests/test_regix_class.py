"""Tests for regix.Regix class and __init__ module exports."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import regix
from regix import Regix, RegressionConfig, Snapshot, SymbolMetrics
from regix.models import GateResult


def _fake_snap(ref: str = "HEAD") -> Snapshot:
    return Snapshot(
        ref=ref, commit_sha="abc123",
        timestamp=datetime.now(timezone.utc),
        workdir=".",
        symbols=[SymbolMetrics(file="a.py", symbol="f", cc=5, mi=50.0)],
    )


class TestRegixInit:
    def test_default_config(self, tmp_path: Path):
        r = Regix(workdir=str(tmp_path))
        assert r.config.workdir == str(tmp_path.resolve())

    def test_string_config(self, tmp_path: Path):
        import yaml
        p = tmp_path / "regix.yaml"
        p.write_text(yaml.dump({"gates": {"hard": {"cc": 22.0}}}))
        r = Regix(config=str(p), workdir=str(tmp_path))
        assert r.config.hard.cc == 22.0

    def test_config_object(self, tmp_path: Path):
        cfg = RegressionConfig()
        cfg.hard.cc = 99.0
        r = Regix(config=cfg, workdir=str(tmp_path))
        assert r.config.hard.cc == 99.0


class TestRegixSnapshot:
    @patch("regix.snapshot.capture")
    def test_snapshot(self, mock_capture, tmp_path: Path):
        mock_capture.return_value = _fake_snap()
        r = Regix(workdir=str(tmp_path))
        snap = r.snapshot("HEAD")
        assert snap.ref == "HEAD"


class TestRegixCompare:
    @patch("regix.snapshot.capture")
    @patch("regix.compare.compare")
    def test_compare(self, mock_compare, mock_capture, tmp_path: Path):
        mock_capture.return_value = _fake_snap()
        mock_compare.return_value = MagicMock(errors=0)
        r = Regix(workdir=str(tmp_path))
        report = r.compare("HEAD~1", "HEAD")
        assert report.errors == 0

    @patch("regix.snapshot.capture")
    @patch("regix.compare.compare")
    def test_compare_local(self, mock_compare, mock_capture, tmp_path: Path):
        mock_capture.return_value = _fake_snap()
        mock_compare.return_value = MagicMock(errors=0)
        r = Regix(workdir=str(tmp_path))
        report = r.compare_local("HEAD")
        assert report.errors == 0


class TestRegixGates:
    @patch("regix.snapshot.capture")
    @patch("regix.gates.check_gates")
    def test_check_gates(self, mock_gates, mock_capture, tmp_path: Path):
        mock_capture.return_value = _fake_snap()
        mock_gates.return_value = GateResult(checks=[])
        r = Regix(workdir=str(tmp_path))
        result = r.check_gates("HEAD")
        assert result.all_passed


class TestModuleExports:
    def test_version(self):
        assert hasattr(regix, "__version__")
        assert isinstance(regix.__version__, str)

    def test_all_exports(self):
        for name in regix.__all__:
            assert hasattr(regix, name)
