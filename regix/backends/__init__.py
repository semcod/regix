"""Backend ABC and registry for static analysis tools."""

from __future__ import annotations

from .base import BackendBase, available_backends, get_backend, register_backend

# Re-export for backward compatibility
__all__ = ["BackendBase", "get_backend", "register_backend", "available_backends"]

# ── Auto-import backends to register them ───────────────────────────────────
# These imports register backends via register_backend() at import time
# ruff: noqa: F401, E402
from .architecture_backend import ArchitectureBackend
from .code2llm_backend import Code2llmBackend
from .coverage_backend import CoverageBackend
from .docstring_backend import DocstringBackend
from .lizard_backend import LizardBackend
from .radon_backend import RadonBackend
from .structure_backend import StructureBackend
from .vallm_backend import VallmBackend
