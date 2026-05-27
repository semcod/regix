"""Architecture backend — AST-based structural metrics for smell detection."""

from __future__ import annotations

import ast
from pathlib import Path

from regix.backends.base import BackendBase, register_backend
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
        return self._python_version()

    def _read_source(
        self,
        workdir: Path,
        fpath: Path,
        sources: dict[str, str] | None,
    ) -> tuple[str, str] | None:
        key = str(fpath)
        if sources and key in sources:
            return key, sources[key]
        full = workdir / fpath
        if not full.exists() or full.suffix != ".py":
            return None
        try:
            return key, full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    @staticmethod
    def _iter_functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        return [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

    @staticmethod
    def _param_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        args = node.args
        count = (
            len(args.args)
            + len(args.posonlyargs)
            + len(args.kwonlyargs)
            + (1 if args.vararg else 0)
            + (1 if args.kwarg else 0)
        )
        if args.args and args.args[0].arg in ("self", "cls"):
            return max(0, count - 1)
        return count

    @staticmethod
    def _is_mock_call(call_node: ast.Call) -> bool:
        """Return True when call node looks like a mock/patch invocation."""
        func = call_node.func
        if isinstance(func, ast.Name):
            name = func.id.lower()
            return name in {"mock", "magicmock", "asyncmock", "patch"}
        if isinstance(func, ast.Attribute):
            attr = func.attr.lower()
            return attr in {"mock", "magicmock", "asyncmock", "patch", "patch.object"}
        return False

    @staticmethod
    def _is_dead_branch(node: ast.AST) -> bool:
        """Return True if node is a branch guarded by a constant false condition."""
        test = None
        if isinstance(node, ast.If):
            test = node.test
        elif isinstance(node, ast.While):
            test = node.test
        if test is None:
            return False
        if isinstance(test, ast.Constant):
            return bool(test.value) is False
        return False

    @staticmethod
    def _except_pass_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
        """Return (except_pass_count, bare_except_count) for function body."""
        except_pass_count = 0
        bare_except_count = 0
        for n in ast.walk(node):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if n.type is None:
                bare_except_count += 1
            if n.body and all(isinstance(stmt, ast.Pass) for stmt in n.body):
                except_pass_count += 1
        return except_pass_count, bare_except_count

    @staticmethod
    def _symbol_metrics(
        fpath: Path,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> SymbolMetrics:
        line_start = node.lineno
        line_end = getattr(node, "end_lineno", node.lineno)
        total_lines = max(line_end - line_start + 1, 1)
        node_walk = list(ast.walk(node))
        stmt_count = sum(1 for n in node_walk if isinstance(n, _STMT_TYPES))
        logic_density = round(stmt_count / total_lines, 3)
        assert_count = sum(1 for n in node_walk if isinstance(n, ast.Assert))
        mock_usage_count = sum(
            1
            for n in node_walk
            if isinstance(n, ast.Call) and ArchitectureBackend._is_mock_call(n)
        )
        dead_branch_count = sum(
            1 for n in node_walk if ArchitectureBackend._is_dead_branch(n)
        )
        except_pass_count, bare_except_count = ArchitectureBackend._except_pass_count(node)
        return SymbolMetrics(
            file=str(fpath),
            symbol=node.name,
            line_start=line_start,
            line_end=line_end,
            call_count=sum(1 for n in node_walk if isinstance(n, ast.Call)),
            param_count=ArchitectureBackend._param_count(node),
            node_type_diversity=len({type(s).__name__ for s in node.body}),
            logic_density=logic_density,
            raw={
                "assert_count": assert_count,
                "mock_usage_count": mock_usage_count,
                "dead_branch_count": dead_branch_count,
                "except_pass_count": except_pass_count,
                "bare_except_count": bare_except_count,
            },
        )

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
        sources: dict[str, str] | None = None,
    ) -> list[SymbolMetrics]:
        results: list[SymbolMetrics] = []
        for fpath in files:
            src = self._read_source(workdir, fpath, sources)
            if src is None:
                continue
            key, source = src
            try:
                tree = ast.parse(source, filename=key)
            except SyntaxError:
                continue
            functions = self._iter_functions(tree)
            for node in functions:
                results.append(self._symbol_metrics(fpath, node))

            # Module-level entry: records function count for god_function detection
            results.append(
                SymbolMetrics(
                    file=str(fpath),
                    symbol=None,
                    raw={"function_count": len(functions)},
                )
            )

        return results


register_backend(ArchitectureBackend())
