"""Radon backend — maintainability index and raw CC."""

from __future__ import annotations

import textwrap
from pathlib import Path

from regix.backends.base import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics


class RadonBackend(BackendBase):
    """Maintainability index and cyclomatic complexity via ``radon``."""

    name = "radon"
    required_binary = None

    def is_available(self) -> bool:
        """True when ``radon`` is importable."""
        try:
            import radon.complexity  # noqa: F401
            import radon.metrics  # noqa: F401

            return True
        except ImportError:
            return False

    def version(self) -> str:
        """Return installed radon version."""
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
        sources: dict[str, str] | None = None,
    ) -> list[SymbolMetrics]:
        """Collect MI and CC using radon.

        MI is module-level by default. With ``mi_granularity == "function"`` an
        additional MI value is computed per function/method from its own source
        span (Halstead volume + CC + SLOC), so that extracting a helper to lower
        CC no longer drops the score the way growing a module's total LOC does
        (regix STARTER-026).
        """
        try:
            from radon.complexity import cc_visit
            from radon.metrics import mi_visit
        except ImportError:
            return []

        per_function_mi = getattr(config, "mi_granularity", "module") == "function"

        results: list[SymbolMetrics] = []
        for fpath in files:
            key = str(fpath)
            if sources and key in sources:
                source = sources[key]
            else:
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

            source_lines = source.splitlines()
            for block in cc_results:
                raw = {
                    "radon_rank": block.letter,
                    "radon_classname": getattr(block, "classname", None),
                }
                fn_mi = None
                if per_function_mi:
                    fn_mi = _function_mi(source_lines, block.lineno, block.endline)
                    raw["radon_mi"] = fn_mi
                results.append(
                    SymbolMetrics(
                        file=str(fpath),
                        symbol=block.name,
                        line_start=block.lineno,
                        line_end=block.endline,
                        cc=block.complexity,
                        mi=fn_mi,
                        raw=raw,
                    )
                )
        return results


def _function_mi(source_lines: list[str], lineno: int, endline: int) -> float | None:
    """Maintainability index for a single function's source span.

    Uses radon's own MI parameters/formula on the dedented function body so the
    score reflects that unit alone, not the whole module's line count.
    """
    try:
        from radon.metrics import mi_compute, mi_parameters
    except ImportError:
        return None
    snippet = "\n".join(source_lines[lineno - 1 : endline])
    if not snippet.strip():
        return None
    dedented = textwrap.dedent(snippet)
    try:
        halstead_volume, complexity, sloc, comments = mi_parameters(dedented, count_multi=True)
        return mi_compute(halstead_volume, complexity, sloc, comments)
    except Exception:
        return None


register_backend(RadonBackend())
