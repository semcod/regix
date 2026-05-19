"""Backend ABC and registry for static analysis tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from regix.config import RegressionConfig
from regix.models import SymbolMetrics

_BACKENDS: dict[str, "BackendBase"] = {}


class BackendBase(ABC):
    """Interface that all analysis backends must implement."""

    name: str = ""
    required_binary: str | None = None

    def is_available(self) -> bool:
        """Return True if the backend's dependencies are installed.

        When *required_binary* is set, checks that the binary is on PATH.
        Built-in backends that set *required_binary* to ``None`` are
        always considered available.
        """
        if self.required_binary is None:
            return True
        import shutil

        return shutil.which(self.required_binary) is not None

    @abstractmethod
    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
        sources: dict[str, str] | None = None,
    ) -> list[SymbolMetrics]:
        """Run analysis and return per-symbol metrics.

        When *sources* is provided it maps ``relative_path → source_text``
        so the backend can work entirely in RAM without touching disk.
        """
        ...

    def version(self) -> str:
        """Return the version string of the backend tool."""
        return "unknown"

    @staticmethod
    def _python_version() -> str:
        """Return the current CPython version (used by builtin AST backends)."""
        import sys

        return f"ast (Python {sys.version_info.major}.{sys.version_info.minor})"


def register_backend(backend: BackendBase) -> None:
    """Register a backend instance for use by Regix."""
    _BACKENDS[backend.name] = backend


def get_backend(name: str) -> BackendBase | None:
    """Look up a registered backend by name."""
    return _BACKENDS.get(name)


def available_backends() -> list[str]:
    """Return names of all registered backends."""
    return list(_BACKENDS.keys())
