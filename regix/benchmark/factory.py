"""Factory functions for building benchmark suites."""

import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from .probes import (
    BackendProbe,
    CLIProbe,
    ImportProbe,
    ThroughputProbe,
    UnitTestProbe,
)
from .suite import BenchmarkSuite

_ROOT = Path(__file__).parent.parent.parent


def build_regix_suite() -> BenchmarkSuite:
    """Build the default regix benchmark suite."""
    suite = BenchmarkSuite("regix")
    suite.add(ImportProbe("regix", threshold=2.0))
    suite.add(ImportProbe("regix.cli", threshold=3.0))
    suite.add(ImportProbe("regix.snapshot", threshold=2.0))
    suite.add(ImportProbe("regix.compare", threshold=2.0))
    suite.add(ImportProbe("regix.config", threshold=1.0))
    suite.add(ImportProbe("regix.models", threshold=1.0))
    suite.add(ImportProbe("regix.backends", threshold=2.0))
    suite.add(
        CLIProbe(
            [sys.executable, "-m", "regix", "--help"],
            label="regix --help",
            threshold=3.0,
        )
    )
    suite.add(
        CLIProbe(
            [sys.executable, "-m", "regix", "status"],
            label="regix status",
            threshold=5.0,
        )
    )
    suite.add(
        CLIProbe(
            [sys.executable, "-m", "regix", "snapshot", "HEAD", "--format", "json"],
            label="regix snapshot HEAD",
            threshold=30.0,
        )
    )
    suite.add(
        CLIProbe(
            [
                sys.executable,
                "-m",
                "regix",
                "compare",
                "HEAD~1",
                "HEAD",
                "--format",
                "json",
            ],
            label="regix compare HEAD~1 HEAD",
            threshold=60.0,
        )
    )
    suite.add(
        CLIProbe(
            [sys.executable, "-m", "regix", "gates"],
            label="regix gates",
            threshold=30.0,
        )
    )
    tests_dir = _ROOT / "tests"
    if tests_dir.exists():
        suite.add(
            UnitTestProbe(
                tests_dir,
                label="full test suite",
                pytest_args=["--ignore", str(tests_dir / "test_benchmark.py")],
                threshold=60.0,
            )
        )
        for test_file in sorted(tests_dir.glob("test_*.py")):
            if test_file.name == "test_benchmark.py":
                continue
            suite.add(
                UnitTestProbe(
                    test_file,
                    label=f"pytest {test_file.name}",
                    threshold=30.0,
                )
            )
    for bk_name, thresh in [
        ("structure", 5.0),
        ("docstring", 5.0),
        ("architecture", 10.0),
        ("lizard", 15.0),
        ("radon", 15.0),
    ]:
        suite.add(
            BackendProbe(
                backend_name=bk_name,
                file_count=20,
                file_size_kb=1.0,
                threshold=thresh,
            )
        )
    suite.add(_make_config_parse_probe())
    suite.add(_make_snapshot_probe())
    suite.add(_make_compare_probe())
    suite.add(_make_gates_probe())
    return suite


def _make_config_parse_probe() -> ThroughputProbe:
    """Benchmark config parsing throughput."""
    _state: dict[str, Any] = {}

    def setup() -> None:
        tmpdir = tempfile.mkdtemp(prefix="regix_bench_cfg_")
        cfg_path = Path(tmpdir) / "regix.yaml"
        cfg_path.write_text(
            textwrap.dedent(
                '            regix:\n              workdir: .\n              metrics:\n                cc_max: 15\n                mi_min: 20\n                coverage_min: 80\n              thresholds:\n                delta_warn: 2\n                delta_error: 5\n              backends:\n                cc: lizard\n                mi: radon\n              exclude:\n                - "tests/**"\n                - ".venv/**"\n        '
            ),
            encoding="utf-8",
        )
        _state["cfg_path"] = str(cfg_path)
        _state["tmpdir"] = tmpdir

    def fn() -> None:
        from regix.config import RegressionConfig

        RegressionConfig.from_file(_state["cfg_path"])

    def teardown() -> None:
        import shutil

        shutil.rmtree(_state.get("tmpdir", ""), ignore_errors=True)

    return ThroughputProbe(
        label="RegressionConfig.from_file()",
        fn=fn,
        n=100,
        setup=setup,
        teardown=teardown,
        threshold_ops=50.0,
    )


def _make_snapshot_probe() -> ThroughputProbe:
    """Benchmark snapshot capture throughput on current HEAD."""
    _state: dict[str, Any] = {}

    def setup() -> None:
        from regix.config import RegressionConfig

        try:
            cfg = RegressionConfig.from_file(_ROOT)
        except FileNotFoundError:
            cfg = RegressionConfig()
        cfg.workdir = str(_ROOT)
        _state["cfg"] = cfg
        _state["wd"] = _ROOT

    def fn() -> None:
        from regix.snapshot import capture

        capture("HEAD", _state["wd"], _state["cfg"])

    return ThroughputProbe(
        label="snapshot.capture(HEAD)",
        fn=fn,
        n=3,
        setup=setup,
        threshold_s=30.0,
    )


def _make_compare_probe() -> ThroughputProbe:
    """Benchmark compare() throughput using two snapshots."""
    _state: dict[str, Any] = {}

    def setup() -> None:
        from regix.config import RegressionConfig
        from regix.snapshot import capture

        try:
            cfg = RegressionConfig.from_file(_ROOT)
        except FileNotFoundError:
            cfg = RegressionConfig()
        cfg.workdir = str(_ROOT)
        _state["cfg"] = cfg
        _state["snap"] = capture("HEAD", _ROOT, cfg)

    def fn() -> None:
        from regix.compare import compare as do_compare

        do_compare(_state["snap"], _state["snap"], _state["cfg"])

    return ThroughputProbe(
        label="compare(HEAD, HEAD)",
        fn=fn,
        n=10,
        setup=setup,
        threshold_ops=5.0,
    )


def _make_gates_probe() -> ThroughputProbe:
    """Benchmark check_gates() throughput."""
    _state: dict[str, Any] = {}

    def setup() -> None:
        from regix.config import RegressionConfig
        from regix.snapshot import capture

        try:
            cfg = RegressionConfig.from_file(_ROOT)
        except FileNotFoundError:
            cfg = RegressionConfig()
        cfg.workdir = str(_ROOT)
        _state["cfg"] = cfg
        _state["snap"] = capture("HEAD", _ROOT, cfg)

    def fn() -> None:
        from regix.gates import check_gates

        check_gates(_state["snap"], _state["cfg"])

    return ThroughputProbe(
        label="check_gates(HEAD)",
        fn=fn,
        n=50,
        setup=setup,
        threshold_ops=20.0,
    )


def benchmark_library(
    module: str,
    cli_commands: list[list[str]] | None = None,
    test_path: Path | None = None,
    threshold_import: float = 2.0,
    threshold_cli: float = 5.0,
    threshold_tests: float = 60.0,
) -> BenchmarkSuite:
    """Build a benchmark suite for an arbitrary Python library.

    Returns a BenchmarkSuite ready to .run(). Useful for comparing regix
    performance against other tools.
    """
    suite = BenchmarkSuite(module)
    suite.add(ImportProbe(module, threshold=threshold_import))
    for cmd in cli_commands or []:
        suite.add(CLIProbe(cmd, threshold=threshold_cli))
    if test_path and test_path.exists():
        suite.add(UnitTestProbe(test_path, threshold=threshold_tests))
    return suite
