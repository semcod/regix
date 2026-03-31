"""Vallm backend — LLM-based code quality scoring via vallm."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from regix.backends import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics


class VallmBackend(BackendBase):
    """LLM-based code quality scoring via the ``vallm`` CLI tool."""

    name = "vallm"
    required_binary = "vallm"

    def is_available(self) -> bool:
        """True when the ``vallm`` binary is on PATH."""
        return shutil.which("vallm") is not None

    def version(self) -> str:
        """Return installed vallm version."""
        try:
            result = subprocess.run(
                ["vallm", "--version"],
                capture_output=True, text=True, check=False,
            )
            return result.stdout.strip() or "unknown"
        except FileNotFoundError:
            return "not installed"

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
        sources: dict[str, str] | None = None,
    ) -> list[SymbolMetrics]:
        """Run ``vallm batch`` and collect quality scores per file."""
        if not self.is_available():
            return []

        results: list[SymbolMetrics] = []
        try:
            proc = subprocess.run(
                ["vallm", "batch", str(workdir), "--recursive", "--format", "json"],
                capture_output=True, text=True, check=False,
                cwd=str(workdir),
            )
            if proc.returncode != 0:
                return results

            data = json.loads(proc.stdout)
            file_set = {str(f) for f in files} if files else set()

            for entry in data if isinstance(data, list) else data.get("files", []):
                fname = entry.get("file", "")
                if file_set and fname not in file_set:
                    continue
                score = entry.get("score", entry.get("quality_score"))
                if score is not None:
                    results.append(
                        SymbolMetrics(
                            file=fname,
                            symbol=None,
                            quality_score=float(score),
                            raw=entry,
                        )
                    )
        except (json.JSONDecodeError, OSError, FileNotFoundError):
            pass

        return results


register_backend(VallmBackend())
