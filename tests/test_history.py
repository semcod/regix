"""Tests for regix.history — aggregation, trends, linear slope, build_history."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from regix.config import RegressionConfig
from regix.git import CommitInfo
from regix.history import (
    _aggregate_snapshot_metrics,
    _compute_trends,
    _linear_slope,
    build_history,
)
from regix.models import CommitMetrics, Snapshot, SymbolMetrics, TrendLine


class TestLinearSlope:
    def test_flat(self):
        assert _linear_slope([5.0, 5.0, 5.0]) == 0.0

    def test_increasing(self):
        slope = _linear_slope([1.0, 2.0, 3.0])
        assert slope > 0

    def test_decreasing(self):
        slope = _linear_slope([3.0, 2.0, 1.0])
        assert slope < 0

    def test_single_value(self):
        assert _linear_slope([5.0]) == 0.0

    def test_empty(self):
        assert _linear_slope([]) == 0.0

    def test_two_values(self):
        slope = _linear_slope([0.0, 10.0])
        assert slope == 10.0


class TestAggregateSnapshotMetrics:
    def test_basic_aggregation(self):
        symbols = [
            SymbolMetrics(file="a.py", symbol="f1", cc=4, mi=40.0, coverage=80.0),
            SymbolMetrics(file="a.py", symbol="f2", cc=6, mi=60.0, coverage=90.0),
        ]
        agg = _aggregate_snapshot_metrics(symbols)
        assert agg["cc_avg"] == 5.0
        assert agg["cc_max"] == 6
        assert agg["mi_avg"] == 50.0
        assert agg["coverage"] == 85.0

    def test_partial_metrics(self):
        symbols = [
            SymbolMetrics(file="a.py", symbol="f1", cc=4),
            SymbolMetrics(file="a.py", symbol="f2", mi=60.0),
        ]
        agg = _aggregate_snapshot_metrics(symbols)
        assert "cc_avg" in agg
        assert "mi_avg" in agg
        assert "coverage" not in agg

    def test_empty_symbols(self):
        agg = _aggregate_snapshot_metrics([])
        assert agg == {}


class TestComputeTrends:
    def _make_cm(self, **metrics) -> CommitMetrics:
        return CommitMetrics(
            sha="abc", ref=None,
            timestamp=datetime.now(timezone.utc),
            author="test", message="test",
            metrics=metrics,
        )

    def test_degrading_cc(self):
        cms = [self._make_cm(cc_avg=3.0), self._make_cm(cc_avg=5.0), self._make_cm(cc_avg=7.0)]
        trends = _compute_trends(cms, ["cc_avg"])
        assert "cc_avg" in trends
        assert trends["cc_avg"].is_degrading  # cc rising = bad

    def test_stable_coverage(self):
        cms = [self._make_cm(coverage=80.0), self._make_cm(coverage=80.0)]
        trends = _compute_trends(cms, ["coverage"])
        assert "coverage" in trends
        assert not trends["coverage"].is_degrading

    def test_too_few_values(self):
        cms = [self._make_cm(cc_avg=3.0)]
        trends = _compute_trends(cms, ["cc_avg"])
        assert "cc_avg" not in trends

    def test_improving_mi(self):
        cms = [self._make_cm(mi_avg=20.0), self._make_cm(mi_avg=30.0), self._make_cm(mi_avg=40.0)]
        trends = _compute_trends(cms, ["mi_avg"])
        assert not trends["mi_avg"].is_degrading  # mi rising = good


def _ci(sha: str) -> CommitInfo:
    return CommitInfo(
        sha=sha, timestamp=datetime.now(timezone.utc),
        author="tom", message="commit",
    )


def _snap(sha: str) -> Snapshot:
    return Snapshot(
        ref=sha, commit_sha=sha,
        timestamp=datetime.now(timezone.utc),
        workdir=".",
        symbols=[SymbolMetrics(file="a.py", symbol="f", cc=5, mi=40.0, coverage=80.0)],
    )


class TestBuildHistory:
    @patch("regix.snapshot.capture")
    @patch("regix.history.list_commits")
    def test_basic(self, mock_list, mock_capture):
        mock_list.return_value = [_ci("abc"), _ci("def")]
        mock_capture.side_effect = [_snap("abc"), _snap("def")]

        report = build_history(
            depth=2, ref="HEAD", workdir=Path("."),
            config=RegressionConfig(),
        )
        assert len(report.commits) == 2
        assert report.commits[0].sha == "abc"
        assert "cc_avg" in report.commits[0].metrics
        assert len(report.trends) > 0

    @patch("regix.snapshot.capture")
    @patch("regix.history.list_commits")
    def test_capture_error_skipped(self, mock_list, mock_capture):
        mock_list.return_value = [_ci("abc"), _ci("def")]
        mock_capture.side_effect = [RuntimeError("git error"), _snap("def")]

        report = build_history(
            depth=2, ref="HEAD", workdir=Path("."),
            config=RegressionConfig(),
        )
        assert len(report.commits) == 1
        assert report.commits[0].sha == "def"

    @patch("regix.snapshot.capture")
    @patch("regix.history.list_commits")
    def test_empty_commits(self, mock_list, mock_capture):
        mock_list.return_value = []
        report = build_history(
            depth=5, ref="HEAD", workdir=Path("."),
            config=RegressionConfig(),
        )
        assert report.commits == []
        assert report.trends == {}

    @patch("regix.snapshot.capture")
    @patch("regix.history.list_commits")
    def test_custom_metrics_filter(self, mock_list, mock_capture):
        mock_list.return_value = [_ci("a"), _ci("b")]
        mock_capture.side_effect = [_snap("a"), _snap("b")]

        report = build_history(
            depth=2, ref="HEAD", workdir=Path("."),
            config=RegressionConfig(),
            metrics_filter=["cc_avg"],
        )
        assert "cc_avg" in report.trends
        assert "mi_avg" not in report.trends
