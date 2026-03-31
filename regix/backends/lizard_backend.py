"""Lizard backend — cyclomatic complexity and function length."""

from __future__ import annotations

import shutil
from pathlib import Path

from regix.backends import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics


class LizardBackend(BackendBase):
    name = "lizard"
    required_binary = "lizard"

    def is_available(self) -> bool:
        try:
            import lizard  # noqa: F401
            return True
        except ImportError:
            return False

    def version(self) -> str:
        try:
            import lizard
            return getattr(lizard, "__version__", "unknown")
        except ImportError:
            return "not installed"

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
    ) -> list[SymbolMetrics]:
        try:
            import lizard
        except ImportError:
            return []

        results: list[SymbolMetrics] = []
        for fpath in files:
            full = workdir / fpath
            if not full.exists() or not full.is_file():
                continue
            try:
                analysis = lizard.analyze_file(str(full))
            except Exception:
                continue

            for func in analysis.function_list:
                results.append(
                    SymbolMetrics(
                        file=str(fpath),
                        symbol=func.name,
                        line_start=func.start_line,
                        line_end=func.end_line,
                        cc=func.cyclomatic_complexity,
                        length=func.nloc,
                        raw={
                            "token_count": func.token_count,
                            "parameter_count": len(func.parameters),
                        },
                    )
                )
        return results


# Auto-register
register_backend(LizardBackend())
