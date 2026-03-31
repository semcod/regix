"""Git helpers — resolve refs, list commits, temporary worktrees."""

from __future__ import annotations

import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from regix.exceptions import GitDirtyError, GitRefError


@dataclass
class CommitInfo:
    """Lightweight commit metadata."""

    sha: str
    timestamp: datetime
    author: str
    message: str


def _run_git(
    args: list[str], workdir: Path = Path("."), check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git"] + args,
        cwd=str(workdir),
        capture_output=True,
        text=True,
        check=check,
    )


def resolve_ref(ref: str, workdir: Path = Path(".")) -> str:
    """Resolve a symbolic ref to a commit SHA.

    Raises GitRefError if the ref cannot be resolved.
    """
    result = _run_git(["rev-parse", "--verify", ref], workdir, check=False)
    if result.returncode != 0:
        raise GitRefError(ref, result.stderr.strip())
    return result.stdout.strip()


def list_commits(
    ref: str = "HEAD",
    depth: int = 20,
    workdir: Path = Path("."),
) -> list[CommitInfo]:
    """Return commit history starting from *ref*, newest first."""
    fmt = "%H%n%aI%n%an%n%s"  # sha, iso-date, author, subject
    result = _run_git(
        ["log", ref, f"--max-count={depth}", f"--format={fmt}"],
        workdir,
    )
    lines = result.stdout.strip().split("\n")
    commits: list[CommitInfo] = []
    i = 0
    while i + 3 < len(lines):
        sha = lines[i]
        ts = datetime.fromisoformat(lines[i + 1])
        author = lines[i + 2]
        message = lines[i + 3]
        commits.append(CommitInfo(sha=sha, timestamp=ts, author=author, message=message))
        i += 4
    return commits


def is_clean(workdir: Path = Path(".")) -> bool:
    """Return True if there are no uncommitted changes."""
    result = _run_git(["status", "--porcelain"], workdir)
    return result.stdout.strip() == ""


def get_dirty_files(workdir: Path = Path(".")) -> list[Path]:
    """Return files with uncommitted changes (modified + untracked)."""
    result = _run_git(["status", "--porcelain"], workdir)
    files: list[Path] = []
    for line in result.stdout.strip().splitlines():
        if line:
            # Format: "XY filename" or "XY filename -> renamed"
            parts = line[3:].split(" -> ")
            files.append(Path(parts[-1]))
    return files


def get_changed_files(ref_a: str, ref_b: str, workdir: Path = Path(".")) -> list[str]:
    """Return list of files changed between two refs."""
    result = _run_git(
        ["diff", "--name-only", ref_a, ref_b],
        workdir,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().splitlines() if f]


@contextmanager
def checkout_temporary(
    ref: str, workdir: Path = Path(".")
) -> Iterator[Path]:
    """Context manager: create a git worktree at *ref* in a temp directory.

    The original working tree is never modified.
    """
    sha = resolve_ref(ref, workdir)
    tmp = Path(tempfile.mkdtemp(prefix="regix_"))
    try:
        _run_git(["worktree", "add", "--detach", str(tmp), sha], workdir)
        yield tmp
    finally:
        _run_git(["worktree", "remove", "--force", str(tmp)], workdir, check=False)
        if tmp.exists():
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
