"""Tests for regix.compare — delta computation and full comparison."""

from __future__ import annotations

from datetime import datetime, timezone

from regix.compare import (
    _collect_deleted_symbol,
    _compare_symbol_metrics,
    _compute_delta,
    compare,
)
from regix.config import RegressionConfig
from regix.models import Snapshot, SymbolMetrics


def _cfg() -> RegressionConfig:
    return RegressionConfig()


class TestComputeDelta:
    def test_both_none(self):
        assert _compute_delta("cc", None, None, _cfg()) is None

    def test_before_none(self):
        assert _compute_delta("cc", None, 5.0, _cfg()) is None

    def test_after_none(self):
        assert _compute_delta("cc", 5.0, None, _cfg()) is None

    def test_no_change(self):
        md = _compute_delta("cc", 5.0, 5.0, _cfg())
        assert md is not None
        assert md.delta == 0.0
        assert not md.is_regression

    def test_cc_increase_is_regression(self):
        md = _compute_delta("cc", 5.0, 15.0, _cfg())
        assert md is not None
        assert md.is_regression
        assert md.delta > 0

    def test_cc_decrease_is_improvement(self):
        md = _compute_delta("cc", 15.0, 5.0, _cfg())
        assert md is not None
        assert md.is_improvement
        assert md.delta < 0

    def test_mi_decrease_is_regression(self):
        md = _compute_delta("mi", 50.0, 30.0, _cfg())
        assert md is not None
        assert md.is_regression

    def test_mi_increase_is_improvement(self):
        md = _compute_delta("mi", 30.0, 50.0, _cfg())
        assert md is not None
        assert md.is_improvement

    def test_error_severity(self):
        md = _compute_delta("cc", 5.0, 20.0, _cfg())
        assert md is not None
        assert md.severity == "error"

    def test_warning_severity(self):
        md = _compute_delta("cc", 5.0, 8.0, _cfg())
        assert md is not None
        assert md.severity in ("warning", "info", "ok")


class TestCollectDeletedSymbol:
    def test_deleted_lower_is_better(self):
        m = SymbolMetrics(file="a.py", symbol="f", cc=10)
        imps = _collect_deleted_symbol(m, "a.py", "f", _cfg(), "ref_a", "ref_b")
        assert len(imps) >= 1
        assert all(i.file == "a.py" for i in imps)

    def test_deleted_no_metrics(self):
        m = SymbolMetrics(file="a.py", symbol="f")
        imps = _collect_deleted_symbol(m, "a.py", "f", _cfg(), "ref_a", "ref_b")
        assert imps == []


class TestCompareSymbolMetrics:
    def test_regression(self):
        m_b = SymbolMetrics(file="a.py", symbol="f", cc=5)
        m_a = SymbolMetrics(file="a.py", symbol="f", cc=20)
        regs, imps, changed = _compare_symbol_metrics(
            m_b, m_a, "a.py", "f", _cfg(), "ref_a", "ref_b",
        )
        assert changed
        assert len(regs) >= 1
        assert regs[0].metric == "cc"

    def test_improvement(self):
        m_b = SymbolMetrics(file="a.py", symbol="f", cc=20)
        m_a = SymbolMetrics(file="a.py", symbol="f", cc=5)
        regs, imps, changed = _compare_symbol_metrics(
            m_b, m_a, "a.py", "f", _cfg(), "ref_a", "ref_b",
        )
        assert changed
        assert len(imps) >= 1

    def test_no_change(self):
        m = SymbolMetrics(file="a.py", symbol="f", cc=5)
        regs, imps, changed = _compare_symbol_metrics(
            m, m, "a.py", "f", _cfg(), "ref_a", "ref_b",
        )
        assert not changed
        assert regs == []
        assert imps == []


def _snap(ref: str, *symbols: SymbolMetrics) -> Snapshot:
    return Snapshot(
        ref=ref, commit_sha="abc",
        timestamp=datetime.now(timezone.utc),
        workdir=".", symbols=list(symbols),
    )


class TestCompare:
    def test_basic_regression(self):
        s_b = _snap("ref_a", SymbolMetrics(file="a.py", symbol="f", cc=5))
        s_a = _snap("ref_b", SymbolMetrics(file="a.py", symbol="f", cc=20))
        report = compare(s_b, s_a, _cfg())
        assert report.errors >= 1
        assert report.has_errors

    def test_basic_improvement(self):
        s_b = _snap("ref_a", SymbolMetrics(file="a.py", symbol="f", cc=20))
        s_a = _snap("ref_b", SymbolMetrics(file="a.py", symbol="f", cc=5))
        report = compare(s_b, s_a, _cfg())
        assert len(report.improvements) >= 1

    def test_no_change(self):
        sym = SymbolMetrics(file="a.py", symbol="f", cc=5)
        s_b = _snap("ref_a", sym)
        s_a = _snap("ref_b", sym)
        report = compare(s_b, s_a, _cfg())
        assert report.errors == 0
        assert report.unchanged >= 1

    def test_new_symbol_not_regression(self):
        s_b = _snap("ref_a")
        s_a = _snap("ref_b", SymbolMetrics(file="a.py", symbol="new_f", cc=50))
        report = compare(s_b, s_a, _cfg())
        assert report.errors == 0

    def test_deleted_symbol_is_improvement(self):
        s_b = _snap("ref_a", SymbolMetrics(file="a.py", symbol="f", cc=10))
        s_a = _snap("ref_b")
        report = compare(s_b, s_a, _cfg())
        assert len(report.improvements) >= 1

    def test_empty_snapshots(self):
        s_b = _snap("ref_a")
        s_a = _snap("ref_b")
        report = compare(s_b, s_a, _cfg())
        assert report.errors == 0
        assert report.unchanged == 0

    def test_report_has_refs(self):
        s_b = _snap("before")
        s_a = _snap("after")
        report = compare(s_b, s_a, _cfg())
        assert report.ref_before == "before"
        assert report.ref_after == "after"

    def test_duration_is_set(self):
        s_b = _snap("ref_a")
        s_a = _snap("ref_b")
        report = compare(s_b, s_a, _cfg())
        assert report.duration >= 0
