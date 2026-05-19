"""CLI entry point for the benchmark runner."""

import argparse
import importlib
import textwrap

from .reporter import BenchmarkReporter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Performance benchmark for regix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            "            Examples:\n              python benchmark.py                     # all suites\n              python benchmark.py --suite startup     # import probes only\n              python benchmark.py --suite cli         # CLI command probes\n              python benchmark.py --suite tests       # unit test probes\n              python benchmark.py --suite backends    # backend throughput\n              python benchmark.py --suite throughput  # in-process throughput\n              python benchmark.py --json              # JSON output\n        "
        ),
    )
    parser.add_argument(
        "--suite",
        choices=["startup", "cli", "tests", "backends", "throughput"],
        default=None,
        help="Run only probes from this suite (default: all)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--plain", action="store_true", help="Plain text (no colours)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="SEC",
        help="Override all time thresholds",
    )
    args = parser.parse_args()
    benchmark_pkg = importlib.import_module("regix.benchmark")
    suite = benchmark_pkg.build_regix_suite()
    results = suite.run(suite_filter=args.suite)
    if args.threshold is not None:
        for r in results:
            if r.unit == "s":
                r.threshold = args.threshold
    fmt = "json" if args.json else "plain" if args.plain else "auto"
    reporter = BenchmarkReporter(results)
    reporter.print(fmt=fmt)
    return 1 if reporter.any_failed() else 0
