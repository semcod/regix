"""Tests for regix.models."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from regix.models import (
    GateCheck,
    GateResult,
    Improvement,
    Regression,
    RegressionReport,
    Snapshot,
    SymbolMetrics,
)


class TestSymbolMetrics:
    def test_creation(self):
        sm = SymbolMetrics(file="src/main.py", symbol="foo", cc=12, length=45)
        assert sm.file == "src/main.py"
        assert sm.symbol == "foo"
        assert sm.cc == 12
        assert sm.length == 45
        assert sm.mi is None

    def test_module_level(self):
        sm = SymbolMetrics(file="src/main.py", mi=42.5)
        assert sm.symbol is None
        assert sm.mi == 42.5


class TestSnapshot:
    def _make_snapshot(self, ref="HEAD", symbols=None):
        return Snapshot(
            ref=ref,
            commit_sha="abc1234",
            timestamp=datetime(2026, 3, 31, tzinfo=timezone.utc),
            workdir=".",
            symbols=symbols or [],
        )

    def test_empty_snapshot(self):
        snap = self._make_snapshot()
        assert snap.ref == "HEAD"
        assert len(snap.symbols) == 0
        assert snap.metrics == {}

    def test_metrics_property(self):
        symbols = [
            SymbolMetrics(file="a.py", symbol="foo", cc=5),
            SymbolMetrics(file="a.py", symbol="bar", cc=10),
            SymbolMetrics(file="b.py", symbol=None, mi=40),
        ]
        snap = self._make_snapshot(symbols=symbols)
        m = snap.metrics
        assert "a.py" in m
        assert "foo" in m["a.py"]
        assert m["a.py"]["foo"].cc == 5
        assert m["b.py"][None].mi == 40

    def test_get(self):
        symbols = [SymbolMetrics(file="a.py", symbol="foo", cc=5)]
        snap = self._make_snapshot(symbols=symbols)
        assert snap.get("a.py", "foo") is not None
        assert snap.get("a.py", "bar") is None
        assert snap.get("missing.py") is None

    def test_save_load(self, tmp_path):
        symbols = [
            SymbolMetrics(file="a.py", symbol="foo", cc=5, length=20),
        ]
        snap = self._make_snapshot(symbols=symbols)
        path = tmp_path / "snap.json"
        snap.save(path)
        assert path.exists()

        loaded = Snapshot.load(path)
        assert loaded.ref == "HEAD"
        assert loaded.commit_sha == "abc1234"
        assert len(loaded.symbols) == 1
        assert loaded.symbols[0].cc == 5


class TestRegressionReport:
    def _make_report(self, regressions=None, improvements=None):
        snap = Snapshot(
            ref="HEAD~1", commit_sha="aaa", timestamp=datetime.now(timezone.utc),
            workdir=".", symbols=[],
        )
        snap2 = Snapshot(
            ref="HEAD", commit_sha="bbb", timestamp=datetime.now(timezone.utc),
            workdir=".", symbols=[],
        )
        regs = regressions or []
        imps = improvements or []
        errors = sum(1 for r in regs if r.severity == "error")
        warnings = sum(1 for r in regs if r.severity == "warning")
        return RegressionReport(
            ref_before="HEAD~1", ref_after="HEAD",
            snapshot_before=snap, snapshot_after=snap2,
            regressions=regs, improvements=imps,
            unchanged=10, errors=errors, warnings=warnings,
        )

    def test_pass_when_no_errors(self):
        report = self._make_report()
        assert report.passed is True
        assert report.has_errors is False
        assert "PASS" in report.summary

    def test_fail_when_errors(self):
        reg = Regression(
            file="a.py", symbol="foo", line=10, metric="cc",
            before=10, after=18, delta=8, severity="error", threshold=5,
        )
        report = self._make_report(regressions=[reg])
        assert report.passed is False
        assert report.has_errors is True
        assert "FAIL" in report.summary

    def test_to_json(self):
        report = self._make_report()
        data = json.loads(report.to_json())
        assert data["regix_schema_version"] == "1"
        assert data["errors"] == 0

    def test_to_yaml(self):
        report = self._make_report()
        text = report.to_yaml()
        assert "regix_schema_version" in text

    def test_to_toon(self):
        reg = Regression(
            file="a.py", symbol="foo", line=10, metric="cc",
            before=10, after=16, delta=6, severity="error", threshold=5,
        )
        report = self._make_report(regressions=[reg])
        toon = report.to_toon()
        assert "ERRORS[1]" in toon
        assert "a.py,foo,cc" in toon

    def test_filter_by_metric(self):
        regs = [
            Regression(file="a.py", symbol="f", line=1, metric="cc",
                       before=5, after=10, delta=5, severity="error", threshold=5),
            Regression(file="a.py", symbol="g", line=5, metric="mi",
                       before=40, after=30, delta=-10, severity="error", threshold=5),
        ]
        report = self._make_report(regressions=regs)
        filtered = report.filter(metric="cc")
        assert len(filtered.regressions) == 1
        assert filtered.regressions[0].metric == "cc"

    def test_filter_by_file(self):
        regs = [
            Regression(file="a.py", symbol="f", line=1, metric="cc",
                       before=5, after=10, delta=5, severity="error", threshold=5),
            Regression(file="b.py", symbol="g", line=5, metric="cc",
                       before=3, after=9, delta=6, severity="error", threshold=5),
        ]
        report = self._make_report(regressions=regs)
        filtered = report.filter(file="a.py")
        assert len(filtered.regressions) == 1


class TestGateResult:
    def test_all_passed(self):
        result = GateResult(checks=[
            GateCheck(metric="cc", value=10, threshold=15, operator="le", passed=True),
        ])
        assert result.all_passed is True

    def test_failure(self):
        result = GateResult(checks=[
            GateCheck(metric="cc", value=20, threshold=15, operator="le", passed=False),
        ])
        assert result.all_passed is False
        assert len(result.errors) == 1
