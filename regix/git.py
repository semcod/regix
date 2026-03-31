"""Git helpers — resolve refs, list commits, temporary worktrees."""

from __future__ import annotations

import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from regix.exceptions import GitRefError


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
    Prefer :func:`read_tree_sources` for in-memory analysis.
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


def read_tree_sources(
    ref: str,
    workdir: Path = Path("."),
    suffix: str = ".py",
) -> dict[str, str]:
    """Read all files matching *suffix* from a git ref entirely in RAM.

    Uses ``git archive`` piped through :mod:`tarfile` so that **no temporary
    files** are created on disk.  Returns ``{relative_path: source_text}``.
    """
    import io
    import tarfile

    sha = resolve_ref(ref, workdir)
    result = subprocess.run(
        ["git", "archive", sha],
        cwd=str(workdir),
        capture_output=True,
        check=True,
    )

    sources: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(suffix):
                continue
            fobj = tar.extractfile(member)
            if fobj is None:
                continue
            try:
                sources[member.name] = fobj.read().decode("utf-8")
            except UnicodeDecodeError:
                continue
    return sources


def read_local_sources(
    workdir: Path,
    files: list[Path],
) -> dict[str, str]:
    """Read source code for *files* from the local working tree into RAM.

    Returns ``{relative_path: source_text}``.  Files that cannot be read
    are silently skipped.
    """
    sources: dict[str, str] = {}
    for fpath in files:
        full = workdir / fpath
        if not full.is_file():
            continue
        try:
            sources[str(fpath)] = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return sources
