"""Tests for regix.compare."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from regix.compare import compare
from regix.config import RegressionConfig
from regix.models import Snapshot, SymbolMetrics


def _snap(ref, symbols):
    return Snapshot(
        ref=ref, commit_sha=f"sha_{ref}",
        timestamp=datetime.now(timezone.utc),
        workdir=".", symbols=symbols,
    )


class TestCompare:
    def test_no_changes(self):
        symbols = [SymbolMetrics(file="a.py", symbol="foo", cc=5)]
        s1 = _snap("before", list(symbols))
        s2 = _snap("after", list(symbols))
        report = compare(s1, s2, RegressionConfig())
        assert report.passed
        assert len(report.regressions) == 0
        assert report.unchanged == 1

    def test_regression_detected(self):
        s1 = _snap("before", [SymbolMetrics(file="a.py", symbol="foo", cc=10)])
        s2 = _snap("after", [SymbolMetrics(file="a.py", symbol="foo", cc=18)])
        cfg = RegressionConfig(delta_warn=2, delta_error=5)
        report = compare(s1, s2, cfg)
        assert len(report.regressions) == 1
        r = report.regressions[0]
        assert r.metric == "cc"
        assert r.before == 10
        assert r.after == 18
        assert r.delta == 8
        assert r.severity == "error"

    def test_improvement_detected(self):
        s1 = _snap("before", [SymbolMetrics(file="a.py", symbol="foo", cc=20)])
        s2 = _snap("after", [SymbolMetrics(file="a.py", symbol="foo", cc=8)])
        report = compare(s1, s2, RegressionConfig())
        assert len(report.improvements) == 1
        imp = report.improvements[0]
        assert imp.metric == "cc"
        assert imp.delta == -12

    def test_mi_regression(self):
        """MI is higher-is-better, so a decrease is a regression."""
        s1 = _snap("before", [SymbolMetrics(file="a.py", symbol=None, mi=45)])
        s2 = _snap("after", [SymbolMetrics(file="a.py", symbol=None, mi=30)])
        cfg = RegressionConfig(delta_warn=5, delta_error=10)
        report = compare(s1, s2, cfg)
        regs = [r for r in report.regressions if r.metric == "mi"]
        assert len(regs) == 1
        assert regs[0].severity == "error"  # delta=15 > error=10

    def test_new_symbol_not_regression(self):
        """A new symbol appearing should not be flagged as regression."""
        s1 = _snap("before", [])
        s2 = _snap("after", [SymbolMetrics(file="a.py", symbol="new_func", cc=20)])
        report = compare(s1, s2, RegressionConfig())
        assert len(report.regressions) == 0

    def test_deleted_symbol_is_improvement(self):
        s1 = _snap("before", [SymbolMetrics(file="a.py", symbol="old_func", cc=25)])
        s2 = _snap("after", [])
        report = compare(s1, s2, RegressionConfig())
        assert len(report.improvements) > 0

    def test_warning_severity(self):
        """Delta between warn and error thresholds should be a warning."""
        s1 = _snap("before", [SymbolMetrics(file="a.py", symbol="f", cc=10)])
        s2 = _snap("after", [SymbolMetrics(file="a.py", symbol="f", cc=13)])
        cfg = RegressionConfig(delta_warn=2, delta_error=5)
        report = compare(s1, s2, cfg)
        assert len(report.regressions) == 1
        assert report.regressions[0].severity == "warning"

    def test_small_delta_ignored(self):
        """Delta below warn threshold should not appear as regression."""
        s1 = _snap("before", [SymbolMetrics(file="a.py", symbol="f", cc=10)])
        s2 = _snap("after", [SymbolMetrics(file="a.py", symbol="f", cc=11)])
        cfg = RegressionConfig(delta_warn=2, delta_error=5)
        report = compare(s1, s2, cfg)
        assert len(report.regressions) == 0

    def test_multiple_files(self):
        s1 = _snap("before", [
            SymbolMetrics(file="a.py", symbol="f", cc=5),
            SymbolMetrics(file="b.py", symbol="g", cc=8),
        ])
        s2 = _snap("after", [
            SymbolMetrics(file="a.py", symbol="f", cc=5),
            SymbolMetrics(file="b.py", symbol="g", cc=20),
        ])
        cfg = RegressionConfig(delta_warn=2, delta_error=5)
        report = compare(s1, s2, cfg)
        assert len(report.regressions) == 1
        assert report.regressions[0].file == "b.py"

    def test_coverage_regression(self):
        """Coverage is higher-is-better, so drop is regression."""
        s1 = _snap("before", [SymbolMetrics(file="a.py", symbol=None, coverage=85)])
        s2 = _snap("after", [SymbolMetrics(file="a.py", symbol=None, coverage=78)])
        cfg = RegressionConfig(delta_warn=2, delta_error=5)
        report = compare(s1, s2, cfg)
        regs = [r for r in report.regressions if r.metric == "coverage"]
        assert len(regs) == 1
        assert regs[0].severity == "error"
