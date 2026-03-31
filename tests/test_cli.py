"""Tests for regix.cli — smoke tests using Typer test runner."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from regix.cli import _load_config, app
from regix.models import (
    Improvement,
    Regression,
    RegressionReport,
    Snapshot,
    SymbolMetrics,
)

runner = CliRunner()


def _fake_snap(ref: str = "HEAD") -> Snapshot:
    return Snapshot(
        ref=ref, commit_sha="abc123",
        timestamp=datetime.now(timezone.utc),
        workdir=".",
        symbols=[SymbolMetrics(file="a.py", symbol="f", cc=5, mi=50.0)],
    )


def _fake_report(**kw) -> RegressionReport:
    defaults = dict(
        ref_before="HEAD~1", ref_after="HEAD",
        snapshot_before=_fake_snap("HEAD~1"),
        snapshot_after=_fake_snap("HEAD"),
        regressions=[], improvements=[], smells=[],
        unchanged=1, errors=0, warnings=0,
        smell_errors=0, smell_warnings=0, stagnated=False, duration=0.01,
    )
    defaults.update(kw)
    return RegressionReport(**defaults)


class TestLoadConfig:
    def test_no_config_file_uses_defaults(self, tmp_path: Path):
        cfg = _load_config(None, str(tmp_path))
        assert cfg.workdir == str(tmp_path.resolve())

    def test_explicit_config(self, tmp_path: Path):
        import yaml
        p = tmp_path / "regix.yaml"
        p.write_text(yaml.dump({"gates": {"hard": {"cc": 22.0}}}))
        cfg = _load_config(str(p), str(tmp_path))
        assert cfg.hard.cc == 22.0

    def test_applies_env_overrides(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("REGIX_CC_MAX", "42")
        cfg = _load_config(None, str(tmp_path))
        assert cfg.cc_max == 42.0


class TestStatusCommand:
    def test_status_runs(self, tmp_path: Path):
        result = runner.invoke(app, ["status", "--workdir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Regix status" in result.output
        assert "Gates" in result.output
        assert "Backends" in result.output


class TestInitCommand:
    def test_init_creates_yaml(self, tmp_path: Path):
        result = runner.invoke(app, ["init", "--workdir", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "regix.yaml").exists()
        assert "Created" in result.output

    def test_init_already_exists(self, tmp_path: Path):
        (tmp_path / "regix.yaml").write_text("existing")
        result = runner.invoke(app, ["init", "--workdir", str(tmp_path)])
        assert result.exit_code == 1
        assert "already exists" in result.output


class TestCompareCommand:
    @patch("regix.snapshot.capture")
    @patch("regix.compare.compare")
    @patch("regix.report.render")
    def test_compare_no_errors(self, mock_render, mock_compare, mock_capture, tmp_path):
        mock_capture.return_value = _fake_snap()
        mock_compare.return_value = _fake_report()
        mock_render.return_value = "report output"
        result = runner.invoke(app, [
            "compare", "HEAD~1", "HEAD",
            "--format", "json", "--workdir", str(tmp_path),
        ])
        assert result.exit_code == 0

    @patch("regix.snapshot.capture")
    @patch("regix.compare.compare")
    @patch("regix.report.render")
    def test_compare_with_errors_exits(self, mock_render, mock_compare, mock_capture, tmp_path):
        mock_capture.return_value = _fake_snap()
        report = _fake_report(errors=1)
        report._has_errors = True
        mock_compare.return_value = report
        mock_render.return_value = "errors found"
        result = runner.invoke(app, [
            "compare", "HEAD~1", "HEAD",
            "--format", "json", "--workdir", str(tmp_path),
        ])
        assert result.exit_code == 1


class TestGatesCommand:
    @patch("regix.snapshot.capture")
    @patch("regix.gates.check_gates")
    def test_gates_all_pass(self, mock_gates, mock_capture, tmp_path):
        from regix.models import GateResult
        mock_capture.return_value = _fake_snap()
        mock_gates.return_value = GateResult(checks=[])
        result = runner.invoke(app, ["gates", "--workdir", str(tmp_path)])
        assert result.exit_code == 0
        assert "passed" in result.output

    @patch("regix.snapshot.capture")
    @patch("regix.gates.check_gates")
    def test_gates_with_errors(self, mock_gates, mock_capture, tmp_path):
        from regix.models import GateCheck, GateResult
        mock_capture.return_value = _fake_snap()
        mock_gates.return_value = GateResult(checks=[
            GateCheck(metric="cc", value=50.0, threshold=15.0,
                      operator="le", passed=False, source="snapshot", severity="error"),
        ])
        result = runner.invoke(app, ["gates", "--workdir", str(tmp_path)])
        assert result.exit_code == 1
        assert "violation" in result.output


class TestDiffCommand:
    @patch("regix.snapshot.capture")
    @patch("regix.compare.compare")
    def test_diff_no_changes(self, mock_compare, mock_capture, tmp_path):
        mock_capture.return_value = _fake_snap()
        mock_compare.return_value = _fake_report()
        result = runner.invoke(app, [
            "diff", "HEAD~1", "HEAD", "--workdir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "No metric changes" in result.output

    @patch("regix.snapshot.capture")
    @patch("regix.compare.compare")
    def test_diff_with_changes(self, mock_compare, mock_capture, tmp_path):
        mock_capture.return_value = _fake_snap()
        reg = Regression(
            file="a.py", symbol="f", line=1, metric="cc",
            before=5.0, after=15.0, delta=10.0, severity="error",
            threshold=5.0, ref_before="HEAD~1", ref_after="HEAD",
        )
        mock_compare.return_value = _fake_report(regressions=[reg], errors=1)
        result = runner.invoke(app, [
            "diff", "HEAD~1", "HEAD", "--workdir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "cc:" in result.output


class TestSnapshotCommand:
    @patch("regix.snapshot.capture")
    def test_snapshot_stdout(self, mock_capture, tmp_path):
        mock_capture.return_value = _fake_snap()
        result = runner.invoke(app, [
            "snapshot", "HEAD", "--workdir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "symbols_count" in result.output
