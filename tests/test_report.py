"""Tests for regix.report rendering."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from regix.models import Improvement, Regression, RegressionReport, Snapshot
from regix.report import render


def _make_snap(ref):
    return Snapshot(
        ref=ref, commit_sha=f"sha_{ref}",
        timestamp=datetime.now(timezone.utc), workdir=".", symbols=[],
    )


class TestRender:
    def _report_with_regressions(self):
        regs = [
            Regression(
                file="cli.py", symbol="bulk_run", line=10, metric="cc",
                before=14, after=19, delta=5, severity="warning", threshold=2,
            ),
            Regression(
                file="validation.py", symbol="validate", line=20, metric="cc",
                before=18, after=26, delta=8, severity="error", threshold=5,
            ),
        ]
        imps = [
            Improvement(
                file="init.py", symbol="collect", line=5, metric="cc",
                before=9, after=6, delta=-3,
            ),
        ]
        return RegressionReport(
            ref_before="HEAD~1", ref_after="HEAD",
            snapshot_before=_make_snap("HEAD~1"),
            snapshot_after=_make_snap("HEAD"),
            regressions=regs, improvements=imps,
            unchanged=10, errors=1, warnings=1,
        )

    def test_rich_format(self):
        report = self._report_with_regressions()
        text = render(report, fmt="rich")
        assert "validation.py" in text
        assert "ERROR" in text
        assert "FAIL" in text

    def test_json_format(self):
        report = self._report_with_regressions()
        text = render(report, fmt="json")
        import json
        data = json.loads(text)
        assert data["errors"] == 1
        assert len(data["regressions"]) == 2

    def test_yaml_format(self):
        report = self._report_with_regressions()
        text = render(report, fmt="yaml")
        assert "regix_schema_version" in text

    def test_toon_format(self):
        report = self._report_with_regressions()
        text = render(report, fmt="toon")
        assert "ERRORS[1]" in text
        assert "WARNINGS[1]" in text
        assert "IMPROVEMENTS[1]" in text

    def test_output_to_file(self, tmp_path):
        report = self._report_with_regressions()
        out = tmp_path / "out.json"
        render(report, fmt="json", output=out)
        assert out.exists()
        import json
        data = json.loads(out.read_text())
        assert data["errors"] == 1

    def test_output_to_directory(self, tmp_path):
        report = self._report_with_regressions()
        render(report, fmt="json", output=tmp_path)
        assert (tmp_path / "report.json").exists()
