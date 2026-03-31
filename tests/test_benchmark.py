"""Tests for regix.benchmark — data model, probes, reporter, suite."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from regix.benchmark import (
    BackendProbe,
    BenchmarkProbe,
    BenchmarkReporter,
    BenchmarkResult,
    BenchmarkSuite,
    CLIProbe,
    ImportProbe,
    ThroughputProbe,
    UnitTestProbe,
    _fmt_time,
    _make_config_parse_probe,
    _make_gates_probe,
    benchmark_library,
    build_regix_suite,
    main,
)


class TestBenchmarkResult:
    def test_ok_no_threshold(self):
        r = BenchmarkResult(name="test", suite="s", elapsed=1.0)
        assert r.status == "OK"
        assert r.passed is True

    def test_pass_under_threshold(self):
        r = BenchmarkResult(name="test", suite="s", elapsed=1.0, threshold=2.0)
        assert r.status == "PASS"
        assert r.passed is True

    def test_fail_over_threshold(self):
        r = BenchmarkResult(name="test", suite="s", elapsed=3.0, threshold=2.0)
        assert r.status == "FAIL"
        assert r.passed is False

    def test_error_status(self):
        r = BenchmarkResult(name="test", suite="s", elapsed=0.0, error="boom")
        assert r.status == "ERROR"
        assert r.passed is False

    def test_to_dict(self):
        r = BenchmarkResult(name="test", suite="s", elapsed=1.234, threshold=2.0)
        d = r.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "PASS"
        assert d["elapsed"] == 1.234
        assert d["threshold"] == 2.0

    def test_to_dict_with_extra(self):
        r = BenchmarkResult(name="t", suite="s", elapsed=0.5, extra={"ops": 100})
        d = r.to_dict()
        assert d["extra"]["ops"] == 100


class TestFmtTime:
    def test_milliseconds(self):
        assert "ms" in _fmt_time(0.005)

    def test_seconds(self):
        assert "s" in _fmt_time(1.5)

    def test_zero(self):
        result = _fmt_time(0.0)
        assert "ms" in result or "s" in result


class TestBenchmarkSuite:
    def test_run_probes(self):
        mock_probe = MagicMock()
        mock_probe.suite = "test"
        mock_probe.run.return_value = BenchmarkResult(
            name="mock", suite="test", elapsed=0.1,
        )
        suite = BenchmarkSuite(name="test_suite")
        suite.add(mock_probe)
        results = suite.run()
        assert len(results) == 1
        assert results[0].name == "mock"
        mock_probe.run.assert_called_once()

    def test_empty_suite(self):
        suite = BenchmarkSuite(name="empty")
        results = suite.run()
        assert results == []

    def test_suite_filter(self):
        p1 = MagicMock()
        p1.suite = "startup"
        p1.run.return_value = BenchmarkResult(name="p1", suite="startup", elapsed=0.1)
        p2 = MagicMock()
        p2.suite = "cli"
        p2.run.return_value = BenchmarkResult(name="p2", suite="cli", elapsed=0.2)
        suite = BenchmarkSuite()
        suite.add(p1)
        suite.add(p2)
        results = suite.run(suite_filter="startup")
        assert len(results) == 1
        assert results[0].name == "p1"


class TestBenchmarkReporter:
    def _results(self) -> list[BenchmarkResult]:
        return [
            BenchmarkResult(name="fast", suite="startup", elapsed=0.1, threshold=1.0),
            BenchmarkResult(name="slow", suite="startup", elapsed=5.0, threshold=2.0),
            BenchmarkResult(name="err", suite="cli", elapsed=0.0, error="failed"),
        ]

    def test_format_result_details_no_extra(self):
        r = BenchmarkResult(name="t", suite="s", elapsed=1.0)
        details = BenchmarkReporter._format_result_details(r)
        assert details == ""

    def test_format_result_details_with_error(self):
        r = BenchmarkResult(name="t", suite="s", elapsed=0.0, error="boom")
        details = BenchmarkReporter._format_result_details(r)
        assert "boom" in details

    def test_format_result_details_with_extra(self):
        r = BenchmarkResult(
            name="t", suite="s", elapsed=1.0,
            extra={"ops_per_sec": 100, "symbols_found": 50, "summary": "done"},
        )
        details = BenchmarkReporter._format_result_details(r)
        assert "100 ops/s" in details
        assert "50 symbols" in details
        assert "done" in details

    def test_print_plain(self, capsys):
        reporter = BenchmarkReporter(self._results())
        reporter.print_plain()
        out = capsys.readouterr().out
        assert "fast" in out
        assert "slow" in out
        assert "FAIL" in out

    def test_print_rich_no_crash(self):
        reporter = BenchmarkReporter(self._results())
        # Just ensure it doesn't crash
        reporter.print_rich()

    def test_print_json(self, capsys):
        reporter = BenchmarkReporter(self._results())
        reporter.print_json()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert len(data) == 3

    def test_print_auto_json(self, capsys):
        reporter = BenchmarkReporter(self._results())
        reporter.print(fmt="json")
        out = capsys.readouterr().out
        assert json.loads(out)

    def test_print_auto_plain(self, capsys):
        reporter = BenchmarkReporter(self._results())
        reporter.print(fmt="plain")
        out = capsys.readouterr().out
        assert "STARTUP" in out

    def test_any_failed(self):
        reporter = BenchmarkReporter(self._results())
        assert reporter.any_failed() is True

    def test_none_failed(self):
        results = [BenchmarkResult(name="ok", suite="s", elapsed=0.1)]
        reporter = BenchmarkReporter(results)
        assert reporter.any_failed() is False


class TestThroughputProbe:
    def test_basic_run(self):
        counter = {"n": 0}
        def fn():
            counter["n"] += 1
        probe = ThroughputProbe(label="counter", fn=fn, n=10)
        result = probe.run()
        assert result.status == "OK"
        assert counter["n"] == 10
        assert "ops_per_sec" in result.extra

    def test_with_threshold_pass(self):
        probe = ThroughputProbe(label="fast", fn=lambda: None, n=5, threshold_s=10.0)
        result = probe.run()
        assert result.status == "PASS"

    def test_with_ops_threshold(self):
        probe = ThroughputProbe(label="fast", fn=lambda: None, n=100, threshold_ops=1.0)
        result = probe.run()
        # 100 ops should take < 100s
        assert result.passed

    def test_with_setup_teardown(self):
        state = {"setup": False, "teardown": False}
        probe = ThroughputProbe(
            label="lifecycle", fn=lambda: None, n=1,
            setup=lambda: state.update(setup=True),
            teardown=lambda: state.update(teardown=True),
        )
        probe.run()
        assert state["setup"] and state["teardown"]

    def test_error_handling(self):
        def boom():
            raise RuntimeError("test error")
        probe = ThroughputProbe(label="boom", fn=boom, n=1)
        result = probe.run()
        assert result.status == "ERROR"
        assert "test error" in result.error


class TestImportProbe:
    def test_import_os(self):
        probe = ImportProbe("os", threshold=5.0, repeat=1)
        result = probe.run()
        assert result.status in ("PASS", "OK")
        assert result.elapsed > 0

    def test_import_nonexistent(self):
        probe = ImportProbe("nonexistent_module_xyz_123", repeat=1)
        result = probe.run()
        assert result.status == "ERROR"


class TestCLIProbe:
    def test_echo(self):
        import sys
        probe = CLIProbe(
            [sys.executable, "-c", "print('hello')"],
            label="echo test", repeat=1, threshold=10.0,
        )
        result = probe.run()
        assert result.status == "PASS"

    def test_command_not_found(self):
        probe = CLIProbe(
            ["__nonexistent_cmd_xyz__"],
            label="missing cmd", repeat=1,
        )
        result = probe.run()
        assert result.status == "ERROR"
        assert "not found" in result.error


class TestUnitTestProbe:
    def test_run_conftest(self, tmp_path: Path):
        test_file = tmp_path / "test_trivial.py"
        test_file.write_text("def test_one(): assert True\n")
        probe = UnitTestProbe(test_file, threshold=30.0, cwd=tmp_path)
        result = probe.run()
        assert result.elapsed > 0
        assert result.status in ("PASS", "OK")


class TestBackendProbe:
    def test_structure_backend(self):
        probe = BackendProbe("structure", file_count=3, threshold=10.0)
        result = probe.run()
        assert result.status in ("PASS", "OK", "FAIL")
        # Should not error — structure backend is always available
        assert result.error is None
        assert result.extra.get("symbols_found", 0) > 0

    def test_nonexistent_backend(self):
        probe = BackendProbe("nonexistent_backend_xyz")
        result = probe.run()
        assert result.status == "ERROR"


class TestBuildRegixSuite:
    def test_suite_created(self):
        suite = build_regix_suite()
        assert suite.name == "regix"
        assert len(suite._probes) > 0


class TestBenchmarkLibrary:
    def test_basic_library(self):
        suite = benchmark_library("os")
        assert suite.name == "os"
        assert len(suite._probes) >= 1

    def test_with_cli_commands(self):
        import sys
        suite = benchmark_library(
            "os",
            cli_commands=[[sys.executable, "-c", "print(1)"]],
            threshold_cli=10.0,
        )
        assert len(suite._probes) >= 2

    def test_with_test_path(self, tmp_path: Path):
        tf = tmp_path / "test_t.py"
        tf.write_text("def test_x(): pass\n")
        suite = benchmark_library("os", test_path=tf)
        assert len(suite._probes) >= 2

    def test_with_nonexistent_test_path(self, tmp_path: Path):
        suite = benchmark_library("os", test_path=tmp_path / "nope")
        # test probe should NOT be added since path doesn't exist
        assert len(suite._probes) >= 1


class TestMakeProbes:
    def test_config_parse_probe(self):
        probe = _make_config_parse_probe()
        assert probe.label == "RegressionConfig.from_file()"
        assert probe.n == 100


class TestMain:
    @patch("regix.benchmark.build_regix_suite")
    def test_main_json(self, mock_build, capsys):
        mock_suite = MagicMock()
        mock_suite.run.return_value = [
            BenchmarkResult(name="t", suite="s", elapsed=0.1),
        ]
        mock_build.return_value = mock_suite
        with patch("sys.argv", ["benchmark.py", "--json"]):
            rc = main()
        assert rc == 0
        out = capsys.readouterr().out
        assert json.loads(out)

    @patch("regix.benchmark.build_regix_suite")
    def test_main_plain(self, mock_build, capsys):
        mock_suite = MagicMock()
        mock_suite.run.return_value = [
            BenchmarkResult(name="ok", suite="s", elapsed=0.5, threshold=1.0),
        ]
        mock_build.return_value = mock_suite
        with patch("sys.argv", ["benchmark.py", "--plain"]):
            rc = main()
        assert rc == 0

    @patch("regix.benchmark.build_regix_suite")
    def test_main_with_threshold_override(self, mock_build, capsys):
        mock_suite = MagicMock()
        mock_suite.run.return_value = [
            BenchmarkResult(name="slow", suite="s", elapsed=10.0, unit="s"),
        ]
        mock_build.return_value = mock_suite
        with patch("sys.argv", ["benchmark.py", "--json", "--threshold", "5.0"]):
            rc = main()
        # 10.0 > 5.0 threshold → FAIL → exit 1
        assert rc == 1

    @patch("regix.benchmark.build_regix_suite")
    def test_main_suite_filter(self, mock_build, capsys):
        mock_suite = MagicMock()
        mock_suite.run.return_value = []
        mock_build.return_value = mock_suite
        with patch("sys.argv", ["benchmark.py", "--suite", "startup", "--json"]):
            main()
        mock_suite.run.assert_called_once_with(suite_filter="startup")
