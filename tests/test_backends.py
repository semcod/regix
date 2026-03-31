"""Tests for regix backends."""

from __future__ import annotations

from pathlib import Path

import pytest

from regix.backends import available_backends, get_backend
from regix.config import RegressionConfig


class TestBackendRegistry:
    def test_docstring_always_available(self):
        bk = get_backend("docstring")
        assert bk is not None
        assert bk.is_available() is True

    def test_available_backends_includes_docstring(self):
        names = available_backends()
        assert "docstring" in names


class TestDocstringBackend:
    def test_full_coverage(self, tmp_path: Path):
        code = tmp_path / "mod.py"
        code.write_text('''\
def hello():
    """Say hello."""
    pass

class Greeter:
    """A greeter."""
    def greet(self):
        """Greet someone."""
        pass
''')
        bk = get_backend("docstring")
        assert bk is not None
        results = bk.collect(tmp_path, [Path("mod.py")], RegressionConfig())
        assert len(results) == 1
        assert results[0].docstring_coverage == 100.0

    def test_partial_coverage(self, tmp_path: Path):
        code = tmp_path / "mod.py"
        code.write_text('''\
def documented():
    """Has a docstring."""
    pass

def undocumented():
    pass
''')
        bk = get_backend("docstring")
        results = bk.collect(tmp_path, [Path("mod.py")], RegressionConfig())
        assert len(results) == 1
        assert results[0].docstring_coverage == 50.0

    def test_no_functions(self, tmp_path: Path):
        code = tmp_path / "empty.py"
        code.write_text("x = 1\n")
        bk = get_backend("docstring")
        results = bk.collect(tmp_path, [Path("empty.py")], RegressionConfig())
        assert len(results) == 1
        assert results[0].docstring_coverage == 100.0  # vacuously true

    def test_skips_private(self, tmp_path: Path):
        code = tmp_path / "mod.py"
        code.write_text('''\
def public_func():
    """Documented."""
    pass

def _private_func():
    pass
''')
        bk = get_backend("docstring")
        results = bk.collect(tmp_path, [Path("mod.py")], RegressionConfig())
        assert results[0].docstring_coverage == 100.0  # _private skipped

    def test_nonexistent_file(self, tmp_path: Path):
        bk = get_backend("docstring")
        results = bk.collect(tmp_path, [Path("missing.py")], RegressionConfig())
        assert len(results) == 0


class TestGates:
    def test_gate_pass(self):
        from regix.gates import check_gates
        from regix.models import Snapshot, SymbolMetrics
        from datetime import datetime, timezone

        snap = Snapshot(
            ref="HEAD", commit_sha="abc",
            timestamp=datetime.now(timezone.utc), workdir=".",
            symbols=[SymbolMetrics(file="a.py", symbol="f", cc=10)],
        )
        from regix.config import GateThresholds
        cfg = RegressionConfig(hard=GateThresholds(cc=15))
        result = check_gates(snap, cfg)
        assert result.all_passed

    def test_gate_fail(self):
        from regix.gates import check_gates
        from regix.models import Snapshot, SymbolMetrics
        from datetime import datetime, timezone

        snap = Snapshot(
            ref="HEAD", commit_sha="abc",
            timestamp=datetime.now(timezone.utc), workdir=".",
            symbols=[SymbolMetrics(file="a.py", symbol="f", cc=20)],
        )
        from regix.config import GateThresholds
        cfg = RegressionConfig(hard=GateThresholds(cc=15))
        result = check_gates(snap, cfg)
        assert not result.all_passed
        assert len(result.errors) == 1
        assert result.errors[0].metric == "cc"
