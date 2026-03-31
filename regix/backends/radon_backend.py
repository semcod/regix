"""Radon backend — maintainability index and raw CC."""

from __future__ import annotations

from pathlib import Path

from regix.backends import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics


class RadonBackend(BackendBase):
    name = "radon"
    required_binary = None

    def is_available(self) -> bool:
        try:
            import radon.complexity  # noqa: F401
            import radon.metrics  # noqa: F401
            return True
        except ImportError:
            return False

    def version(self) -> str:
        try:
            import radon
            return getattr(radon, "__version__", "unknown")
        except ImportError:
            return "not installed"

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
    ) -> list[SymbolMetrics]:
        try:
            from radon.complexity import cc_visit
            from radon.metrics import mi_visit
        except ImportError:
            return []

        results: list[SymbolMetrics] = []
        for fpath in files:
            full = workdir / fpath
            if not full.exists() or full.suffix != ".py":
                continue
            try:
                source = full.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # Maintainability index (module-level)
            try:
                mi = mi_visit(source, multi=True)
            except Exception:
                mi = None

            # CC per function/class
            try:
                cc_results = cc_visit(source)
            except Exception:
                cc_results = []

            # Module-level entry with MI
            results.append(
                SymbolMetrics(
                    file=str(fpath),
                    symbol=None,
                    mi=mi,
                    raw={"radon_mi": mi},
                )
            )

            for block in cc_results:
                results.append(
                    SymbolMetrics(
                        file=str(fpath),
                        symbol=block.name,
                        line_start=block.lineno,
                        line_end=block.endline,
                        cc=block.complexity,
                        raw={
                            "radon_rank": block.letter,
                            "radon_classname": getattr(block, "classname", None),
                        },
                    )
                )
        return results


register_backend(RadonBackend())
