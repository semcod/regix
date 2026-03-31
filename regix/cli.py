"""Regix CLI — Typer-based command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="regix",
    help="Regression Index — detect and measure code quality regressions between git versions.",
    add_completion=False,
)


def _load_config(config: str | None, workdir: str) -> "RegressionConfig":
    from regix.config import RegressionConfig

    wd = Path(workdir).resolve()
    if config:
        cfg = RegressionConfig.from_file(config)
    else:
        try:
            cfg = RegressionConfig.from_file(wd)
        except FileNotFoundError:
            cfg = RegressionConfig()
    cfg.workdir = str(wd)
    cfg.apply_env_overrides()
    return cfg


@app.command()
def compare(
    ref_a: str = typer.Argument("HEAD~1", help="Base ref"),
    ref_b: str = typer.Argument("HEAD", help="Target ref (or 'local' with --local)"),
    local: bool = typer.Option(False, "--local", help="Compare REF_A against the current working tree"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to regix.yaml"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich | json | yaml | toon"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write report to file/dir"),
    metric: Optional[list[str]] = typer.Option(None, "--metric", "-m", help="Filter to specific metric(s)"),
    errors_only: bool = typer.Option(False, "--errors-only", help="Suppress warnings"),
    fail_on: str = typer.Option("error", "--fail-on", help="Exit 1 on: error | warning"),
    workdir: str = typer.Option(".", "--workdir", "-w", help="Project root"),
):
    """Compare metrics between two git refs or local state."""
    from regix.compare import compare as do_compare
    from regix.report import render
    from regix.snapshot import capture

    cfg = _load_config(config, workdir)
    wd = Path(cfg.workdir).resolve()

    if local:
        ref_b = "local"

    snap_a = capture(ref_a, wd, cfg)
    snap_b = capture(ref_b, wd, cfg)
    report = do_compare(snap_a, snap_b, cfg)

    # Apply filters
    if metric:
        for m in metric:
            report = report.filter(metric=m)
    if errors_only:
        report = report.filter(severity="error")

    text = render(report, fmt=fmt, output=output)
    if not output:
        typer.echo(text)

    # Exit code
    if fail_on == "warning" and (report.has_errors or report.warnings > 0):
        raise SystemExit(cfg.fail_exit_code)
    if report.has_errors:
        raise SystemExit(cfg.fail_exit_code)


@app.command()
def history(
    depth: int = typer.Option(20, "--depth", "-d", help="Number of commits to scan"),
    ref: str = typer.Option("HEAD", "--ref", help="Starting ref"),
    metric: Optional[list[str]] = typer.Option(None, "--metric", "-m", help="Metrics to include"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich | json | yaml | csv"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write to file"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to regix.yaml"),
    workdir: str = typer.Option(".", "--workdir", "-w", help="Project root"),
):
    """Show metric timeline across N historical commits."""
    from regix.history import build_history
    from regix.report import render_history

    cfg = _load_config(config, workdir)
    wd = Path(cfg.workdir).resolve()

    report = build_history(
        depth=depth, ref=ref, workdir=wd, config=cfg, metrics_filter=metric
    )
    text = render_history(report, fmt=fmt)

    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        typer.echo(text)


@app.command()
def snapshot(
    ref: str = typer.Argument("HEAD", help="Git ref to snapshot"),
    fmt: str = typer.Option("json", "--format", "-f", help="Output format: json | yaml"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write to file"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to regix.yaml"),
    workdir: str = typer.Option(".", "--workdir", "-w", help="Project root"),
):
    """Capture and store a snapshot without comparing."""
    from regix.snapshot import capture

    cfg = _load_config(config, workdir)
    wd = Path(cfg.workdir).resolve()

    snap = capture(ref, wd, cfg)

    if output:
        snap.save(output)
        typer.echo(f"Snapshot saved to {output}")
    else:
        import json
        from dataclasses import asdict
        data = {
            "ref": snap.ref,
            "commit_sha": snap.commit_sha,
            "timestamp": snap.timestamp.isoformat(),
            "symbols_count": len(snap.symbols),
            "backend_versions": snap.backend_versions,
            "symbols": [asdict(s) for s in snap.symbols[:50]],
        }
        typer.echo(json.dumps(data, indent=2, default=str))


@app.command()
def diff(
    ref_a: str = typer.Argument("HEAD~1", help="Base ref"),
    ref_b: str = typer.Argument("HEAD", help="Target ref"),
    threshold: float = typer.Option(0.0, "--threshold", help="Min delta to show"),
    metric: Optional[list[str]] = typer.Option(None, "--metric", "-m", help="Filter metric(s)"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to regix.yaml"),
    workdir: str = typer.Option(".", "--workdir", "-w", help="Project root"),
):
    """Show symbol-by-symbol metric diff (like git diff for metrics)."""
    from regix.compare import compare as do_compare
    from regix.snapshot import capture

    cfg = _load_config(config, workdir)
    wd = Path(cfg.workdir).resolve()

    snap_a = capture(ref_a, wd, cfg)
    snap_b = capture(ref_b, wd, cfg)
    report = do_compare(snap_a, snap_b, cfg)

    # Build diff-style output
    all_items = []
    for r in report.regressions:
        if abs(r.delta) >= threshold:
            if metric and r.metric not in metric:
                continue
            sign = "+" if r.delta > 0 else ""
            all_items.append(
                f"  {r.file}::{r.symbol or '(mod)'}  "
                f"{r.metric}: {r.before} → {r.after} ({sign}{r.delta})"
            )
    for i in report.improvements:
        if abs(i.delta) >= threshold:
            if metric and i.metric not in metric:
                continue
            sign = "+" if i.delta > 0 else ""
            all_items.append(
                f"  {i.file}::{i.symbol or '(mod)'}  "
                f"{i.metric}: {i.before} → {i.after} ({sign}{i.delta})"
            )

    if all_items:
        typer.echo(f"Metric diff: {ref_a} → {ref_b}")
        typer.echo("─" * 60)
        for line in sorted(all_items):
            typer.echo(line)
    else:
        typer.echo("No metric changes detected.")


@app.command()
def gates(
    ref: str = typer.Option("HEAD", "--ref", help="Git ref to check"),
    fail_on: str = typer.Option("error", "--fail-on", help="Exit 1 on: error | any"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to regix.yaml"),
    workdir: str = typer.Option(".", "--workdir", "-w", help="Project root"),
):
    """Check current state against configured quality gates (absolute thresholds)."""
    from regix.gates import check_gates
    from regix.snapshot import capture

    cfg = _load_config(config, workdir)
    wd = Path(cfg.workdir).resolve()

    snap = capture(ref, wd, cfg)
    result = check_gates(snap, cfg)

    if result.all_passed:
        typer.echo("✓ All quality gates passed.")
    else:
        typer.echo(f"✗ {len(result.errors)} gate violation(s):")
        for gc in result.errors:
            op_str = {"le": "≤", "ge": "≥", "eq": "="}.get(gc.operator, gc.operator)
            typer.echo(
                f"  {gc.metric}: {gc.value} (threshold: {op_str} {gc.threshold})"
            )
        raise SystemExit(cfg.fail_exit_code)


@app.command()
def status(
    config: Optional[str] = typer.Option(None, "--config", help="Path to regix.yaml"),
    workdir: str = typer.Option(".", "--workdir", "-w", help="Project root"),
):
    """Show Regix configuration and available backends."""
    from regix.backends import available_backends, get_backend

    cfg = _load_config(config, workdir)

    typer.echo("Regix status")
    typer.echo("─" * 40)
    typer.echo(f"  workdir:   {cfg.workdir}")
    typer.echo(f"  cc_max:    {cfg.cc_max}")
    typer.echo(f"  mi_min:    {cfg.mi_min}")
    typer.echo(f"  coverage:  {cfg.coverage_min}")
    typer.echo(f"  format:    {cfg.output_format}")
    typer.echo("")
    typer.echo("Backends:")
    for name in available_backends():
        bk = get_backend(name)
        if bk:
            avail = "✓" if bk.is_available() else "✗"
            typer.echo(f"  {avail} {name:<15s}  {bk.version()}")


@app.command()
def init(
    workdir: str = typer.Option(".", "--workdir", "-w", help="Project root"),
):
    """Create a default regix.yaml in the project root."""
    wd = Path(workdir).resolve()
    target = wd / "regix.yaml"
    if target.exists():
        typer.echo(f"regix.yaml already exists at {target}")
        raise SystemExit(1)

    default_config = """\
regix:
  workdir: .

  metrics:
    cc_max: 15
    mi_min: 20
    coverage_min: 80
    length_max: 100

  thresholds:
    delta_warn: 2
    delta_error: 5

  backends:
    cc: lizard
    mi: radon
    coverage: pytest-cov
    quality: none
    docstring: builtin

  exclude:
    - "tests/**"
    - "docs/**"
    - "examples/**"
    - ".venv/**"

  output:
    format: rich
    dir: .regix/
    show_improvements: true

  gates:
    on_regression: warn
"""
    target.write_text(default_config, encoding="utf-8")
    typer.echo(f"Created {target}")


if __name__ == "__main__":
    app()
