"""Lizard backend — cyclomatic complexity and function length."""

from __future__ import annotations

from pathlib import Path

from regix.backends import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics


class LizardBackend(BackendBase):
    """Cyclomatic complexity and function length via the ``lizard`` library."""

    name = "lizard"
    required_binary = "lizard"

    def is_available(self) -> bool:
        """True when the ``lizard`` package is importable."""
        try:
            import lizard  # noqa: F401
            return True
        except ImportError:
            return False

    def version(self) -> str:
        """Return installed lizard version."""
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
        sources: dict[str, str] | None = None,
    ) -> list[SymbolMetrics]:
        """Collect CC and length per function using lizard."""
        try:
            import lizard
        except ImportError:
            return []

        results: list[SymbolMetrics] = []
        for fpath in files:
            key = str(fpath)
            try:
                if sources and key in sources:
                    analysis = lizard.analyze_source_code(sources[key], key)
                else:
                    full = workdir / fpath
                    if not full.exists() or not full.is_file():
                        continue
                    analysis = lizard.analyze_file(str(full))
            except Exception:
                continue

            for func in analysis.function_list:
                results.append(
                    SymbolMetrics(
                        file=key,
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
