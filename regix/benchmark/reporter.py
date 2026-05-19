"""Benchmark reporter — formats results as tables, plain text, or JSON."""

import json
from typing import Dict, List

from .models import BenchmarkResult

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    _RICH = True
except ImportError:
    _RICH = False


def _fmt_time(s: float) -> str:
    if s < 0.001:
        return f"{s * 1000:.2f} ms"
    if s < 1.0:
        return f"{s * 1000:.1f} ms"
    return f"{s:.3f}  s"


class BenchmarkReporter:
    """Prints results as a rich table or plain text."""

    def __init__(self, results: List[BenchmarkResult]):
        self.results = results

    @staticmethod
    def _format_result_details(r: BenchmarkResult) -> str:
        """Build the details string for a single benchmark result."""
        if not r.extra and (not r.error):
            return ""
        if not r.extra:
            return f"[red]{r.error[:80]}[/red]" if r.error else ""
        _EXTRA_KEYS = (
            ("ops_per_sec", "ops/s"),
            ("files_per_sec", "files/s"),
            ("symbols_found", "symbols"),
            ("summary", None),
        )
        parts = []
        for key, suffix in _EXTRA_KEYS:
            if key in r.extra:
                parts.append(f"{r.extra[key]} {suffix}" if suffix else r.extra[key])
        if r.error:
            parts.append(f"[red]{r.error[:60]}[/red]")
        return "  ".join(parts)

    def print_rich(self) -> None:
        console = Console()
        console.print()
        console.print(Panel.fit("[bold cyan]Regix Performance Benchmark[/bold cyan]"))
        suites: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            suites.setdefault(r.suite, []).append(r)
        _STATUS_COLORS = {
            "OK": "green",
            "PASS": "green",
            "FAIL": "red",
            "ERROR": "bold red",
        }
        for suite_name, suite_results in suites.items():
            table = Table(
                title=f"[bold]{suite_name.upper()}[/bold]",
                box=box.SIMPLE_HEAVY,
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Probe", style="cyan", min_width=35)
            table.add_column("Time", justify="right", min_width=12)
            table.add_column("Threshold", justify="right", min_width=12)
            table.add_column("Status", justify="center", min_width=8)
            table.add_column("Details", style="dim")
            for r in suite_results:
                sc = _STATUS_COLORS.get(r.status, "white")
                table.add_row(
                    r.name,
                    _fmt_time(r.elapsed) if not r.error else "—",
                    _fmt_time(r.threshold) if r.threshold else "—",
                    f"[{sc}]{r.status}[/{sc}]",
                    self._format_result_details(r),
                )
            console.print(table)
        total = len(self.results)
        passed = sum((1 for r in self.results if r.status in ("OK", "PASS")))
        failed = sum((1 for r in self.results if r.status == "FAIL"))
        errors = sum((1 for r in self.results if r.status == "ERROR"))
        console.print(
            f"[bold]Total:[/bold] {total}  [green]OK/PASS: {passed}[/green]  [red]FAIL: {failed}[/red]  [bold red]ERROR: {errors}[/bold red]"
        )
        console.print()

    def print_plain(self) -> None:
        suites: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            suites.setdefault(r.suite, []).append(r)
        for suite_name, suite_results in suites.items():
            print(f"\n{'=' * 65}")
            print(f"  {suite_name.upper()}")
            print(f"{'=' * 65}")
            print(f"  {'Probe':<40} {'Time':>10}  {'Status':>8}")
            print(f"  {'-' * 62}")
            for r in suite_results:
                t = _fmt_time(r.elapsed) if not r.error else "—"
                print(f"  {r.name:<40} {t:>10}  {r.status:>8}")
                if r.extra.get("summary"):
                    print(f"    → {r.extra['summary']}")
                if r.error:
                    print(f"    ! {r.error[:80]}")

    def print_json(self) -> None:
        print(json.dumps([r.to_dict() for r in self.results], indent=2))

    def print(self, fmt: str = "auto") -> None:
        if fmt == "json":
            self.print_json()
        elif fmt == "plain" or not _RICH:
            self.print_plain()
        else:
            self.print_rich()

    def any_failed(self) -> bool:
        return any((r.status in ("FAIL", "ERROR") for r in self.results))
