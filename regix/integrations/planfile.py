"""Planfile integration — automatic ticket generation from regressions."""

from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from regix.models import RegressionReport, Regression


def sync_regressions_to_planfile(report: RegressionReport, workdir: str = ".") -> List[str]:
    """Generates planfile tickets for regressions and syncs them to TODO.md."""
    wd = Path(workdir).resolve()
    tickets_created = []

    # 1. Find planfile executable
    planfile_bin = shutil.which("planfile")
    # Fallback to local copy if present
    local_planfile = Path("/home/tom/github/semcod/planfile/.venv/bin/planfile")
    if not planfile_bin and local_planfile.exists():
        planfile_bin = str(local_planfile)

    if not planfile_bin:
        print("⚠️ planfile executable not found. Regression ticket generation skipped.")
        return []

    # 2. Iterate and create tickets for regressions
    for reg in report.regressions:
        symbol_name = reg.symbol or "(module)"
        title = f"[Regression] {reg.metric.upper()} worsened in {symbol_name}"
        desc = (
            f"Regression detected in {reg.file} at {symbol_name}.\n"
            f"Metric '{reg.metric}' changed from {reg.before} to {reg.after} "
            f"(delta: {reg.delta:+.2f}).\n"
            f"Configured threshold: {reg.threshold}."
        )
        priority = "high" if reg.severity == "error" else "normal"
        labels = ["bug", "regression", "regix", reg.metric, "llm-ready"]

        cmd = [
            planfile_bin, "ticket", "create", title,
            "-p", priority,
            "-d", desc,
            "--files", reg.file,
            "--source", "regix"
        ]
        for label in labels:
            cmd.extend(["-l", label])

        try:
            # Create the ticket
            res = subprocess.run(
                cmd, capture_output=True, text=True, check=True, cwd=str(wd)
            )
            ticket_id_match = res.stdout.strip()
            print(f"✅ Created planfile ticket for regression in {reg.file} ({symbol_name})")
            tickets_created.append(ticket_id_match)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create planfile ticket: {e.stderr or e.stdout}")
        except Exception as e:
            print(f"❌ Error invoking planfile: {e}")

    # 3. Synchronize with TODO.md
    if tickets_created:
        print("🔄 Syncing tickets to TODO.md via planfile sync...")
        sync_cmd = [planfile_bin, "sync", "markdown", "--direction", "to"]
        try:
            subprocess.run(sync_cmd, capture_output=True, text=True, check=True, cwd=str(wd))
            print("✅ Successfully synced new regression tickets to TODO.md!")
        except Exception as e:
            print(f"❌ Failed to sync tickets to markdown: {e}")

    return tickets_created
