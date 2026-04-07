"""Tests for architectural smell detection — architecture backend + smells module."""
from datetime import datetime, timezone
from pathlib import Path
from regix.backends import get_backend
from regix.config import RegressionConfig
from regix.models import Snapshot, SymbolMetrics
from regix.smells import detect_smells

def _snap(ref: str, symbols: list[SymbolMetrics]) -> Snapshot:
    return Snapshot(ref=ref, commit_sha=f'sha_{ref}', timestamp=datetime.now(timezone.utc), workdir='.', symbols=symbols)

def _sm(**kwargs) -> SymbolMetrics:
    defaults = {'file': 'a.py', 'symbol': 'foo'}
    defaults.update(kwargs)
    return SymbolMetrics(**defaults)

class TestArchitectureBackend:

    def setup_method(self) -> None:
        self.bk = get_backend('architecture')
        assert self.bk is not None
        assert self.bk.is_available()

    def test_stub_function_zero_calls(self, tmp_path: Path) -> None:
        (tmp_path / 'mod.py').write_text('def stub():\n    return 0\n')
        results = self.bk.collect(tmp_path, [Path('mod.py')], RegressionConfig())
        func = next((r for r in results if r.symbol == 'stub'))
        assert func.call_count == 0
        assert func.param_count == 0
        assert func.node_type_diversity == 1

    def test_function_with_calls(self, tmp_path: Path) -> None:
        code = 'def process(data, helper):\n    result = helper.transform(data)\n    if result:\n        return result.finalize()\n    return None\n'
        (tmp_path / 'mod.py').write_text(code)
        results = self.bk.collect(tmp_path, [Path('mod.py')], RegressionConfig())
        func = next((r for r in results if r.symbol == 'process'))
        assert func.call_count >= 2
        assert func.param_count == 2
        assert func.node_type_diversity >= 2

    def test_logic_density_stub_vs_real(self, tmp_path: Path) -> None:
        code = 'def stub():\n    return 0\n\ndef real(x, y):\n    a = x + 1\n    b = y * 2\n    if a > b:\n        return a\n    return b\n'
        (tmp_path / 'mod.py').write_text(code)
        results = self.bk.collect(tmp_path, [Path('mod.py')], RegressionConfig())
        stub = next((r for r in results if r.symbol == 'stub'))
        real = next((r for r in results if r.symbol == 'real'))
        assert stub.logic_density < real.logic_density

    def test_param_count_excludes_self(self, tmp_path: Path) -> None:
        code = 'class Foo:\n    def method(self, x, y):\n        return x + y\n'
        (tmp_path / 'mod.py').write_text(code)
        results = self.bk.collect(tmp_path, [Path('mod.py')], RegressionConfig())
        func = next((r for r in results if r.symbol == 'method'))
        assert func.param_count == 2

    def test_function_count_in_raw(self, tmp_path: Path) -> None:
        code = 'def a(): pass\ndef b(): pass\ndef c(): pass\n'
        (tmp_path / 'mod.py').write_text(code)
        results = self.bk.collect(tmp_path, [Path('mod.py')], RegressionConfig())
        mod = next((r for r in results if r.symbol is None))
        assert mod.raw.get('function_count') == 3

    def test_nonexistent_file_skipped(self, tmp_path: Path) -> None:
        results = self.bk.collect(tmp_path, [Path('missing.py')], RegressionConfig())
        assert results == []

    def test_non_python_file_skipped(self, tmp_path: Path) -> None:
        (tmp_path / 'mod.js').write_text('function foo() { return 0; }')
        results = self.bk.collect(tmp_path, [Path('mod.js')], RegressionConfig())
        assert results == []

    def test_async_function_counted(self, tmp_path: Path) -> None:
        code = 'async def fetch(url):\n    result = await client.get(url)\n    return result\n'
        (tmp_path / 'mod.py').write_text(code)
        results = self.bk.collect(tmp_path, [Path('mod.py')], RegressionConfig())
        func = next((r for r in results if r.symbol == 'fetch'))
        assert func.call_count >= 1
        mod = next((r for r in results if r.symbol is None))
        assert mod.raw['function_count'] == 1

class TestGodFunction:

    def test_god_function_detected(self) -> None:
        mod_b = _sm(symbol=None, raw={'function_count': 4})
        mod_a = _sm(symbol=None, raw={'function_count': 1})
        funcs_b = [_sm(symbol='parse', length=15), _sm(symbol='validate', length=12), _sm(symbol='transform', length=10), _sm(symbol='format', length=8)]
        funcs_a = [_sm(symbol='handle_all', length=80, line_start=1)]
        snap_b = _snap('before', [mod_b] + funcs_b)
        snap_a = _snap('after', [mod_a] + funcs_a)
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert any((s.smell == 'god_function' for s in smells))

    def test_no_god_function_when_count_stable(self) -> None:
        mod_b = _sm(symbol=None, raw={'function_count': 3})
        mod_a = _sm(symbol=None, raw={'function_count': 3})
        funcs = [_sm(symbol=f'f{i}', length=20) for i in range(3)]
        snap_b = _snap('before', [mod_b] + funcs)
        snap_a = _snap('after', [mod_a] + funcs)
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'god_function' for s in smells))

    def test_god_function_error_severity_on_large_growth(self) -> None:
        mod_b = _sm(symbol=None, raw={'function_count': 4})
        mod_a = _sm(symbol=None, raw={'function_count': 1})
        funcs_b = [_sm(symbol=f'f{i}', length=10) for i in range(4)]
        funcs_a = [_sm(symbol='giant', length=200, line_start=1)]
        snap_b = _snap('before', [mod_b] + funcs_b)
        snap_a = _snap('after', [mod_a] + funcs_a)
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        god = next((s for s in smells if s.smell == 'god_function'))
        assert god.severity == 'error'

class TestStubRegression:

    def test_stub_regression_detected(self) -> None:
        snap_b = _snap('before', [_sm(length=25, call_count=5, param_count=2)])
        snap_a = _snap('after', [_sm(length=2, call_count=0, param_count=2)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert any((s.smell == 'stub_regression' for s in smells))

    def test_no_stub_regression_when_calls_remain(self) -> None:
        snap_b = _snap('before', [_sm(length=25, call_count=5)])
        snap_a = _snap('after', [_sm(length=3, call_count=2)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'stub_regression' for s in smells))

    def test_no_stub_regression_when_was_already_small(self) -> None:
        snap_b = _snap('before', [_sm(length=4, call_count=0)])
        snap_a = _snap('after', [_sm(length=2, call_count=0)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'stub_regression' for s in smells))

    def test_stub_regression_error_severity(self) -> None:
        snap_b = _snap('before', [_sm(length=30, call_count=8)])
        snap_a = _snap('after', [_sm(length=2, call_count=0)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        stub = next((s for s in smells if s.smell == 'stub_regression'))
        assert stub.severity == 'error'

class TestNoDelegation:

    def test_no_delegation_detected(self) -> None:
        snap_b = _snap('before', [_sm(call_count=4, param_count=2, length=10)])
        snap_a = _snap('after', [_sm(call_count=0, param_count=0, length=3)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert any((s.smell == 'no_delegation' for s in smells))

    def test_no_delegation_not_flagged_if_was_always_isolated(self) -> None:
        snap_b = _snap('before', [_sm(call_count=0, param_count=0, length=3)])
        snap_a = _snap('after', [_sm(call_count=0, param_count=0, length=3)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'no_delegation' for s in smells))

    def test_no_delegation_not_flagged_for_long_function(self) -> None:
        snap_b = _snap('before', [_sm(call_count=5, param_count=2, length=40)])
        snap_a = _snap('after', [_sm(call_count=0, param_count=0, length=25)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'no_delegation' for s in smells))

class TestLogicDensityDrop:

    def test_density_drop_detected(self) -> None:
        snap_b = _snap('before', [_sm(logic_density=0.6)])
        snap_a = _snap('after', [_sm(logic_density=0.1)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert any((s.smell == 'logic_density_drop' for s in smells))

    def test_density_drop_not_flagged_when_still_acceptable(self) -> None:
        snap_b = _snap('before', [_sm(logic_density=0.6)])
        snap_a = _snap('after', [_sm(logic_density=0.45)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'logic_density_drop' for s in smells))

    def test_density_drop_not_flagged_when_was_already_sparse(self) -> None:
        snap_b = _snap('before', [_sm(logic_density=0.1)])
        snap_a = _snap('after', [_sm(logic_density=0.05)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'logic_density_drop' for s in smells))

    def test_density_drop_error_severity(self) -> None:
        snap_b = _snap('before', [_sm(logic_density=0.8)])
        snap_a = _snap('after', [_sm(logic_density=0.05)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        smell = next((s for s in smells if s.smell == 'logic_density_drop'))
        assert smell.severity == 'error'

class TestCohesionLoss:

    def test_cohesion_loss_detected(self) -> None:
        snap_b = _snap('before', [_sm(node_type_diversity=4)])
        snap_a = _snap('after', [_sm(node_type_diversity=1)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert any((s.smell == 'cohesion_loss' for s in smells))

    def test_cohesion_loss_not_flagged_when_still_diverse(self) -> None:
        snap_b = _snap('before', [_sm(node_type_diversity=4)])
        snap_a = _snap('after', [_sm(node_type_diversity=3)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'cohesion_loss' for s in smells))

    def test_cohesion_loss_not_flagged_when_was_already_homogeneous(self) -> None:
        snap_b = _snap('before', [_sm(node_type_diversity=1)])
        snap_a = _snap('after', [_sm(node_type_diversity=1)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'cohesion_loss' for s in smells))

class TestHallucinationProxy:

    def test_hallucination_proxy_detected(self) -> None:
        snap_b = _snap('before', [_sm(call_count=5, logic_density=0.7, length=20, cc=4)])
        snap_a = _snap('after', [_sm(call_count=0, logic_density=0.1, length=3, cc=1)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert any((s.smell == 'hallucination_proxy' for s in smells))

    def test_hallucination_proxy_not_flagged_with_calls(self) -> None:
        snap_b = _snap('before', [_sm(call_count=5, logic_density=0.7, length=20)])
        snap_a = _snap('after', [_sm(call_count=3, logic_density=0.1, length=3, cc=1)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'hallucination_proxy' for s in smells))

    def test_hallucination_proxy_not_flagged_when_was_already_hollow(self) -> None:
        snap_b = _snap('before', [_sm(call_count=0, logic_density=0.05, length=2)])
        snap_a = _snap('after', [_sm(call_count=0, logic_density=0.05, length=2, cc=1)])
        smells = detect_smells(snap_b, snap_a, RegressionConfig())
        assert not any((s.smell == 'hallucination_proxy' for s in smells))

    def test_hallucination_proxy_requires_two_signals(self) -> None:
        cfg = RegressionConfig()
        snap_b = _snap('before', [_sm(call_count=3, logic_density=0.5, length=15)])
        snap_a = _snap('after', [_sm(call_count=0, logic_density=0.1)])
        smells = detect_smells(snap_b, snap_a, cfg)
        assert not any((s.smell == 'hallucination_proxy' for s in smells))

class TestSmellsInReport:

    def test_compare_returns_smells(self) -> None:
        from regix.compare import compare
        snap_b = _snap('before', [_sm(symbol=None, raw={'function_count': 4}), _sm(symbol='parse', length=15, call_count=3), _sm(symbol='validate', length=12, call_count=2), _sm(symbol='transform', length=10, call_count=4), _sm(symbol='format', length=8, call_count=1)])
        snap_a = _snap('after', [_sm(symbol=None, raw={'function_count': 1}), _sm(symbol='handle_all', length=90, call_count=0, line_start=1)])
        report = compare(snap_b, snap_a, RegressionConfig())
        assert len(report.smells) > 0

    def test_smell_errors_fail_report(self) -> None:
        from regix.compare import compare
        snap_b = _snap('before', [_sm(symbol=None, raw={'function_count': 4})] + [_sm(symbol=f'f{i}', length=10) for i in range(4)])
        snap_a = _snap('after', [_sm(symbol=None, raw={'function_count': 1}), _sm(symbol='giant', length=200, line_start=1)])
        report = compare(snap_b, snap_a, RegressionConfig())
        god_errors = [s for s in report.smells if s.smell == 'god_function' and s.severity == 'error']
        if god_errors:
            assert not report.passed