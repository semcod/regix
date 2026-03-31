"""Architecture backend — AST-based structural metrics for smell detection."""

from __future__ import annotations

import ast
from pathlib import Path

from regix.backends import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics

# Statement node types that count as "meaningful logic"
_STMT_TYPES = (
    ast.Assign,
    ast.AugAssign,
    ast.AnnAssign,
    ast.If,
    ast.For,
    ast.While,
    ast.With,
    ast.Try,
    ast.Return,
    ast.Raise,
    ast.Delete,
    ast.Assert,
    ast.Expr,
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
)


class ArchitectureBackend(BackendBase):
    """Computes per-function structural metrics via AST for smell detection."""

    name = "architecture"
    required_binary = None

    def is_available(self) -> bool:
        return True

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

            func_count = 0
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue

                func_count += 1

                # param_count — total parameters excluding self/cls
                args = node.args
                param_count = (
                    len(args.args)
                    + len(args.posonlyargs)
                    + len(args.kwonlyargs)
                    + (1 if args.vararg else 0)
                    + (1 if args.kwarg else 0)
                )
                if args.args and args.args[0].arg in ("self", "cls"):
                    param_count = max(0, param_count - 1)

                # call_count — all Call nodes inside this function (incl. nested)
                call_count = sum(
                    1 for n in ast.walk(node) if isinstance(n, ast.Call)
                )

                # node_type_diversity — unique direct-body statement type names
                node_type_diversity = len({type(s).__name__ for s in node.body})

                # logic_density — meaningful statement nodes / total lines
                line_start = node.lineno
                line_end = getattr(node, "end_lineno", node.lineno)
                total_lines = max(line_end - line_start + 1, 1)
                stmt_count = sum(
                    1 for n in ast.walk(node) if isinstance(n, _STMT_TYPES)
                )
                logic_density = round(stmt_count / total_lines, 3)

                results.append(
                    SymbolMetrics(
                        file=str(fpath),
                        symbol=node.name,
                        line_start=line_start,
                        line_end=line_end,
                        call_count=call_count,
                        param_count=param_count,
                        node_type_diversity=node_type_diversity,
                        logic_density=logic_density,
                    )
                )

            # Module-level entry: records function count for god_function detection
            results.append(
                SymbolMetrics(
                    file=str(fpath),
                    symbol=None,
                    raw={"function_count": func_count},
                )
            )

        return results


register_backend(ArchitectureBackend())
