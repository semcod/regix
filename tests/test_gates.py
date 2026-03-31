"""Tests for regix.gates — gate evaluation against snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

from regix.config import RegressionConfig
from regix.gates import _passes, check_gates
from regix.models import Snapshot, SymbolMetrics


class TestPasses:
    def test_le_pass(self):
        assert _passes(5.0, 10.0, "le") is True

    def test_le_fail(self):
        assert _passes(15.0, 10.0, "le") is False

    def test_le_equal(self):
        assert _passes(10.0, 10.0, "le") is True

    def test_ge_pass(self):
        assert _passes(90.0, 80.0, "ge") is True

    def test_ge_fail(self):
        assert _passes(70.0, 80.0, "ge") is False

    def test_ge_equal(self):
        assert _passes(80.0, 80.0, "ge") is True

    def test_eq_pass(self):
        assert _passes(5.0, 5.0, "eq") is True

    def test_eq_fail(self):
        assert _passes(5.0, 6.0, "eq") is False


def _snap_with_symbols(*symbols: SymbolMetrics) -> Snapshot:
    return Snapshot(
        ref="HEAD", commit_sha="abc123",
        timestamp=datetime.now(timezone.utc),
        workdir=".", symbols=list(symbols),
    )


class TestCheckGates:
    def test_all_pass(self):
        sym = SymbolMetrics(file="a.py", symbol="f", cc=3, mi=50.0, coverage=95.0, length=20)
        snap = _snap_with_symbols(sym)
        result = check_gates(snap, RegressionConfig())
        assert result.all_passed

    def test_hard_gate_fails(self):
        sym = SymbolMetrics(file="a.py", symbol="f", cc=50, mi=5.0)
        snap = _snap_with_symbols(sym)
        result = check_gates(snap, RegressionConfig())
        assert not result.all_passed
        errors = [c for c in result.checks if c.severity == "error"]
        assert len(errors) > 0

    def test_target_warning(self):
        # cc=12: passes hard (15) but fails target (10)
        sym = SymbolMetrics(file="a.py", symbol="f", cc=12)
        snap = _snap_with_symbols(sym)
        result = check_gates(snap, RegressionConfig())
        warnings = [c for c in result.checks if c.severity == "warning"]
        assert len(warnings) >= 1

    def test_none_metrics_skipped(self):
        sym = SymbolMetrics(file="a.py", symbol="f")  # all None
        snap = _snap_with_symbols(sym)
        result = check_gates(snap, RegressionConfig())
        assert result.all_passed
        assert len(result.checks) == 0

    def test_multiple_symbols(self):
        s1 = SymbolMetrics(file="a.py", symbol="f1", cc=3)
        s2 = SymbolMetrics(file="b.py", symbol="f2", cc=50)  # fails hard
        snap = _snap_with_symbols(s1, s2)
        result = check_gates(snap, RegressionConfig())
        assert not result.all_passed
