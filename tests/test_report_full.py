"""Tests for regix.report — render and render_history."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from regix.models import (
    CommitMetrics,
    HistoryReport,
    Improvement,
    Regression,
    RegressionReport,
    Snapshot,
    SymbolMetrics,
    TrendLine,
)
from regix.report import render, render_history


def _empty_snap(ref: str = "HEAD") -> Snapshot:
    return Snapshot(
        ref=ref, commit_sha="abc",
        timestamp=datetime.now(timezone.utc),
        workdir=".", symbols=[],
    )


def _report(**overrides) -> RegressionReport:
    defaults = dict(
        ref_before="HEAD~1",
        ref_after="HEAD",
        snapshot_before=_empty_snap("HEAD~1"),
        snapshot_after=_empty_snap("HEAD"),
        regressions=[],
        improvements=[],
        smells=[],
        unchanged=0,
        errors=0,
        warnings=0,
        smell_errors=0,
        smell_warnings=0,
        stagnated=False,
        duration=0.1,
    )
    defaults.update(overrides)
    return RegressionReport(**defaults)


class TestRender:
    def test_json_format(self):
        text = render(_report(), fmt="json")
        assert '"ref_before"' in text

    def test_yaml_format(self):
        text = render(_report(), fmt="yaml")
        assert "ref_before" in text

    def test_toon_format(self):
        text = render(_report(), fmt="toon")
        assert "SUMMARY:" in text

    def test_unknown_format_falls_back(self):
        # Should not crash on unknown format
        text = render(_report(), fmt="rich")
        assert text is not None

    def test_with_regressions(self):
        reg = Regression(
            file="a.py", symbol="func", line=10,
            metric="cc", before=5.0, after=15.0, delta=10.0,
            severity="error", threshold=5.0,
            ref_before="HEAD~1", ref_after="HEAD",
        )
        text = render(_report(regressions=[reg], errors=1), fmt="toon")
        assert "ERRORS" in text

    def test_with_improvements(self):
        imp = Improvement(
            file="a.py", symbol="func", line=10,
            metric="cc", before=15.0, after=5.0, delta=-10.0,
            ref_before="HEAD~1", ref_after="HEAD",
        )
        text = render(_report(improvements=[imp]), fmt="toon")
        assert "IMPROVEMENTS" in text


class TestRenderHistory:
    def _history(self) -> HistoryReport:
        cms = [
            CommitMetrics(
                sha="abc1234", ref=None,
                timestamp=datetime.now(timezone.utc),
                author="tom", message="init",
                metrics={"cc_avg": 5.0, "cc_max": 10, "mi_avg": 40.0, "coverage": 80.0},
            ),
            CommitMetrics(
                sha="def5678", ref=None,
                timestamp=datetime.now(timezone.utc),
                author="tom", message="fix",
                metrics={"cc_avg": 4.0, "cc_max": 8, "mi_avg": 45.0, "coverage": 85.0},
            ),
        ]
        trends = {
            "cc_avg": TrendLine(metric="cc_avg", values=[5.0, 4.0], slope=-1.0, is_degrading=False),
        }
        return HistoryReport(commits=cms, regressions=[], trends=trends)

    def test_rich_format(self):
        text = render_history(self._history(), fmt="rich")
        assert "abc1234" in text or "abc123" in text

    def test_json_format(self):
        text = render_history(self._history(), fmt="json")
        assert "cc_avg" in text

    def test_yaml_format(self):
        text = render_history(self._history(), fmt="yaml")
        assert "cc_avg" in text

    def test_csv_format(self):
        text = render_history(self._history(), fmt="csv")
        assert "sha" in text or "cc_avg" in text
