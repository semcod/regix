"""Report rendering — rich tables, JSON, YAML, TOON output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from regix.models import HistoryReport, RegressionReport


def render(
    report: RegressionReport,
    fmt: str = "rich",
    output: str | Path | None = None,
) -> str:
    """Render a regression report in the specified format."""
    if fmt == "json":
        text = report.to_json()
    elif fmt == "yaml":
        text = report.to_yaml()
    elif fmt == "toon":
        text = report.to_toon()
    elif fmt == "rich":
        text = _render_rich(report)
    else:
        text = report.to_json()

    if output:
        p = Path(output)
        p.parent.mkdir(parents=True, exist_ok=True)
        ext = {"json": ".json", "yaml": ".yaml", "toon": ".toon.yaml"}.get(fmt, ".txt")
        if p.is_dir():
            p = p / f"report{ext}"
        p.write_text(text, encoding="utf-8")

    return text


def _render_rich(report: RegressionReport) -> str:
    """Render a rich-formatted text report (no Rich library dependency for basic output)."""
    lines: list[str] = []
    lines.append(f"Regression Report: {report.ref_before} → {report.ref_after}")
    lines.append("═" * 60)

    # Group regressions by file
    files: dict[str, list[Any]] = {}
    for r in report.regressions:
        files.setdefault(r.file, []).append(r)

    for fname in sorted(files):
        lines.append(f"  {fname}")
        for r in files[fname]:
            arrow = "▲" if r.delta > 0 else "▼"
            sign = "+" if r.delta > 0 else ""
            mark = "✗" if r.severity == "error" else "⚠"
            name = r.symbol or "(module)"
            lines.append(
                f"    {arrow} {name:<30s}  {r.metric}  "
                f"{r.before} → {r.after}  ({sign}{r.delta})   "
                f"{mark} {r.severity.upper()}"
            )
        lines.append("")

    if report.improvements:
        lines.append("Improvements:")
        for i in report.improvements[:10]:
            name = i.symbol or "(module)"
            sign = "+" if i.delta > 0 else ""
            lines.append(
                f"    ✓ {i.file}::{name}  {i.metric}  "
                f"{i.before} → {i.after}  ({sign}{i.delta})"
            )
        if len(report.improvements) > 10:
            lines.append(f"    ... and {len(report.improvements) - 10} more")
        lines.append("")

    status = "✗ FAIL" if report.has_errors else "✓ PASS"
    lines.append(
        f"Summary: {report.errors} error(s), {report.warnings} warning(s), "
        f"{len(report.improvements)} improvement(s)"
    )
    lines.append(f"Gates: {status}")

    return "\n".join(lines)


def render_history(
    report: HistoryReport,
    fmt: str = "rich",
) -> str:
    """Render a history report."""
    if fmt == "json":
        import json
        data = {
            "commits": [
                {
                    "sha": cm.sha[:7],
                    "author": cm.author,
                    "message": cm.message,
                    "metrics": cm.metrics,
                }
                for cm in report.commits
            ],
            "trends": {
                k: {"slope": t.slope, "is_degrading": t.is_degrading}
                for k, t in report.trends.items()
            },
        }
        return json.dumps(data, indent=2, default=str)

    # Rich text table
    lines: list[str] = []
    header = f"{'Commit':<10s}  {'cc_avg':>7s}  {'cc_max':>7s}  {'coverage':>9s}  {'mi_avg':>7s}"
    lines.append(header)
    lines.append("─" * len(header))
    for cm in report.commits:
        m = cm.metrics
        lines.append(
            f"{cm.sha[:7]:<10s}  "
            f"{m.get('cc_avg', '-'):>7}  "
            f"{m.get('cc_max', '-'):>7}  "
            f"{str(m.get('coverage', '-')) + ' %':>9s}  "
            f"{m.get('mi_avg', '-'):>7}"
        )

    if report.trends:
        lines.append("")
        lines.append("Trends:")
        for name, trend in report.trends.items():
            direction = "↗ degrading" if trend.is_degrading else "→ stable"
            lines.append(f"  {name}: slope={trend.slope}  {direction}")

    return "\n".join(lines)
