"""Structure backend — AST-based architectural regression metrics.

Measures per function:
  - fan_out      unique external function/method calls (delegation depth)
  - call_count   total ast.Call nodes in body

Measures per file (symbol=None):
  - symbol_count  number of functions and methods defined in the file
"""

from __future__ import annotations

import ast
from pathlib import Path

from regix.backends import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics

_PYTHON_BUILTINS = frozenset({
    "print", "len", "range", "type", "isinstance", "issubclass", "hasattr",
    "getattr", "setattr", "delattr", "callable", "iter", "next", "enumerate",
    "zip", "map", "filter", "sorted", "reversed", "list", "dict", "set",
    "tuple", "str", "int", "float", "bool", "bytes", "repr", "abs", "round",
    "min", "max", "sum", "any", "all", "open", "super", "vars", "dir",
    "id", "hash", "hex", "oct", "bin", "chr", "ord", "format", "input",
    "staticmethod", "classmethod", "property", "object",
})


class _CallVisitor(ast.NodeVisitor):
    """Collect call_count and fan_out from a function body."""

    def __init__(self) -> None:
        self.call_count: int = 0
        self.called_names: set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        self.call_count += 1
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name not in _PYTHON_BUILTINS:
                self.called_names.add(name)
        elif isinstance(node.func, ast.Attribute):
            # obj.method() — attribute call
            val = node.func.value
            if isinstance(val, ast.Name) and val.id == "self":
                # self.method() — internal delegation
                self.called_names.add(f"self.{node.func.attr}")
            else:
                self.called_names.add(node.func.attr)
        self.generic_visit(node)


def _analyse_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
    """Return (call_count, fan_out) for a single function node."""
    visitor = _CallVisitor()
    for child in ast.iter_child_nodes(node):
        visitor.visit(child)
    return visitor.call_count, len(visitor.called_names)


class StructureBackend(BackendBase):
    """AST-based structural metrics: fan_out, call_count, symbol_count."""

    name = "structure"
    required_binary = None

    def is_available(self) -> bool:
        """Always available — pure-Python, no external deps."""
        return True

    def version(self) -> str:
        """Return Python version used for AST parsing."""
        import sys
        return f"ast (Python {sys.version_info.major}.{sys.version_info.minor})"

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
        sources: dict[str, str] | None = None,
    ) -> list[SymbolMetrics]:
        """Collect fan_out, call_count per function and symbol_count per file."""
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

            func_nodes: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]] = []
            self._collect_functions(tree, func_nodes)

            # File-level: symbol_count
            results.append(SymbolMetrics(
                file=str(fpath),
                symbol=None,
                symbol_count=len(func_nodes),
                raw={"structure_symbol_count": len(func_nodes)},
            ))

            # Per-function: fan_out, call_count
            for node, qualified_name in func_nodes:
                call_count, fan_out = _analyse_function(node)
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                results.append(SymbolMetrics(
                    file=str(fpath),
                    symbol=qualified_name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    call_count=call_count,
                    fan_out=fan_out,
                    raw={
                        "structure_call_count": call_count,
                        "structure_fan_out": fan_out,
                    },
                ))

        return results

    def _collect_functions(
        self,
        tree: ast.AST,
        out: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, str]],
        prefix: str = "",
    ) -> None:
        """Walk the AST and collect all function/method definitions with qualified names."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qname = f"{prefix}{node.name}" if prefix else node.name
                out.append((node, qname))
                # recurse into nested functions
                self._collect_functions(node, out, prefix=f"{qname}.")
            elif isinstance(node, ast.ClassDef):
                self._collect_functions(node, out, prefix=f"{node.name}.")


register_backend(StructureBackend())
