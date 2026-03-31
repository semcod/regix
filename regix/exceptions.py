"""Regix exceptions — typed, structured errors."""

from __future__ import annotations


class RegixError(Exception):
    """Base exception for all Regix errors."""


class GitRefError(RegixError):
    """Raised when a git ref cannot be resolved."""

    def __init__(self, ref: str, detail: str = ""):
        self.ref = ref
        msg = f"Cannot resolve git ref '{ref}'"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class GitDirtyError(RegixError):
    """Raised when the working tree is dirty and the operation requires a clean state."""

    def __init__(self, dirty_files: list[str]):
        self.dirty_files = dirty_files
        count = len(dirty_files)
        super().__init__(
            f"Working tree has {count} uncommitted change(s). "
            "Commit or stash before comparing non-local refs."
        )


class BackendError(RegixError):
    """Raised when a backend fails to produce output."""

    def __init__(self, backend: str, cause: Exception | None = None):
        self.backend = backend
        self.cause = cause
        msg = f"Backend '{backend}' failed"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


class ConfigError(RegixError):
    """Raised when the configuration file is invalid."""

    def __init__(self, detail: str, path: str | None = None):
        self.path = path
        self.detail = detail
        msg = f"Configuration error: {detail}"
        if path:
            msg += f" (in {path})"
        super().__init__(msg)
