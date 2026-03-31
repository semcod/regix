"""Tests for regix.integrations — RegixCollector and REGIX_PRESET."""

from __future__ import annotations

import json
from pathlib import Path

from regix.integrations import REGIX_PRESET, RegixCollector


class TestRegixCollector:
    def test_no_report_returns_zeros(self, tmp_path: Path):
        c = RegixCollector()
        result = c.collect(tmp_path)
        assert result == {"regression_errors": 0, "regression_warnings": 0}

    def test_json_report(self, tmp_path: Path):
        d = tmp_path / ".regix"
        d.mkdir()
        (d / "report.json").write_text(json.dumps({"errors": 3, "warnings": 1}))
        result = RegixCollector().collect(tmp_path)
        assert result["regression_errors"] == 3
        assert result["regression_warnings"] == 1

    def test_toon_report_errors_section(self, tmp_path: Path):
        d = tmp_path / ".regix"
        d.mkdir()
        (d / "report.toon.yaml").write_text(
            "ERRORS[2]{file,symbol}:\n  a.py,f1\n  b.py,f2\nWARNINGS[5]{file}:\n  c.py\n"
        )
        result = RegixCollector().collect(tmp_path)
        assert result["regression_errors"] == 2
        assert result["regression_warnings"] == 5


class TestRegixCollectorToonEdgeCases:
    def test_toon_errors_line_format(self, tmp_path: Path):
        d = tmp_path / ".regix"
        d.mkdir()
        (d / "report.toon.yaml").write_text(
            "errors: 4\nwarnings: 2\n"
        )
        result = RegixCollector().collect(tmp_path)
        assert result["regression_errors"] == 4

    def test_toon_malformed_values(self, tmp_path: Path):
        d = tmp_path / ".regix"
        d.mkdir()
        (d / "report.toon.yaml").write_text(
            "ERRORS[bad]{file}:\nWARNINGS[bad]{file}:\n"
        )
        result = RegixCollector().collect(tmp_path)
        assert result["regression_errors"] == 0
        assert result["regression_warnings"] == 0

    def test_json_report_missing_keys(self, tmp_path: Path):
        d = tmp_path / ".regix"
        d.mkdir()
        (d / "report.json").write_text(json.dumps({}))
        result = RegixCollector().collect(tmp_path)
        assert result["regression_errors"] == 0
        assert result["regression_warnings"] == 0


class TestRegixPreset:
    def test_has_required_keys(self):
        assert "binary" in REGIX_PRESET
        assert "command" in REGIX_PRESET
        assert REGIX_PRESET["binary"] == "regix"
