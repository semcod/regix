"""Docstring backend — pure Python, ast-based docstring coverage."""

from __future__ import annotations

import ast
from pathlib import Path

from regix.backends import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics


class DocstringBackend(BackendBase):
    name = "docstring"
    required_binary = None

    def is_available(self) -> bool:
        return True  # Built-in, always available

    def version(self) -> str:
        import sys
        return f"ast (Python {sys.version_info.major}.{sys.version_info.minor})"

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
        sources: dict[str, str] | None = None,
    ) -> list[SymbolMetrics]:
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
            try:
                tree = ast.parse(source, filename=key)
            except SyntaxError:
                continue

            total = 0
            documented = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Skip private/dunder unless it's __init__
                    name = node.name
                    if name.startswith("_") and name != "__init__":
                        continue
                    total += 1
                    docstring = ast.get_docstring(node)
                    if docstring:
                        documented += 1

            pct = (documented / total * 100) if total > 0 else 100.0
            results.append(
                SymbolMetrics(
                    file=str(fpath),
                    symbol=None,
                    docstring_coverage=round(pct, 1),
                    raw={"total_public": total, "documented": documented},
                )
            )
        return results


register_backend(DocstringBackend())
