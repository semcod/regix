"""Pyqual integration — gate collector and tool preset."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

try:
    from pyqual.tools import ToolPreset
except ImportError:
    ToolPreset = None  # type: ignore


class AttributePreset(dict):
    """Dict-compatible preset with attribute access for pyqual callers."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class RegixCollector:
    """GateSet-compatible metric collector for pyqual.

    Reads ``.regix/report.toon.yaml`` and returns
    ``{"regression_errors": N, "regression_warnings": N}``.
    """

    def collect(self, workdir: Path) -> dict[str, Any]:
        """Read regix report and extract gate-relevant metrics."""
        candidates = [
            workdir / ".regix" / "report.toon.yaml",
            workdir / ".regix" / "report.json",
        ]
        for path in candidates:
            if path.exists():
                return self._parse(path)
        return {"regression_errors": 0, "regression_warnings": 0}

    def _parse(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(text)
            return {
                "regression_errors": data.get("errors", 0),
                "regression_warnings": data.get("warnings", 0),
            }
        # TOON format: parse SUMMARY line
        errors = 0
        warnings = 0
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("errors:"):
                try:
                    errors = int(line.split(":")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
            if line.startswith("ERRORS["):
                try:
                    errors = int(line.split("[")[1].split("]")[0])
                except (ValueError, IndexError):
                    pass
            if line.startswith("WARNINGS["):
                try:
                    warnings = int(line.split("[")[1].split("]")[0])
                except (ValueError, IndexError):
                    pass
        return {"regression_errors": errors, "regression_warnings": warnings}


# Tool preset for pyqual
if ToolPreset is not None:
    _preset = ToolPreset(
        binary="regix",
        command="regix compare HEAD~1 HEAD --format toon --output .regix/",
        output=".regix/report.toon.yaml",
        allow_failure=False,
    )
else:
    # Fallback dla backward compatibility gdy pyqual nie jest zainstalowany
    _preset = SimpleNamespace(
        binary="regix",
        command="regix compare HEAD~1 HEAD --format toon --output .regix/",
        output=".regix/report.toon.yaml",
        allow_failure=False,
    )


def _as_attribute_preset(value: Any) -> AttributePreset:
    if isinstance(value, dict):
        return AttributePreset(value)
    if hasattr(value, "__dict__"):
        return AttributePreset(vars(value))
    return AttributePreset(
        {
            "binary": getattr(value, "binary", "regix"),
            "command": getattr(
                value,
                "command",
                "regix compare HEAD~1 HEAD --format toon --output .regix/",
            ),
            "output": getattr(value, "output", ".regix/report.toon.yaml"),
            "allow_failure": getattr(value, "allow_failure", False),
        }
    )


REGIX_PRESET = _as_attribute_preset(_preset)
