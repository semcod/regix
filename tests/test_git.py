"""Tests for regix.git — helpers that don't need a real git repo."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from regix.exceptions import GitRefError
from regix.git import (
    CommitInfo,
    get_changed_files,
    get_dirty_files,
    is_clean,
    list_commits,
    read_local_sources,
    resolve_ref,
)


class TestResolveRef:
    @patch("regix.git._run_git")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n")
        sha = resolve_ref("HEAD")
        assert sha == "abc1234"

    @patch("regix.git._run_git")
    def test_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stderr="bad ref")
        with pytest.raises(GitRefError):
            resolve_ref("nonexistent")


class TestIsClean:
    @patch("regix.git._run_git")
    def test_clean(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        assert is_clean() is True

    @patch("regix.git._run_git")
    def test_dirty(self, mock_run):
        mock_run.return_value = MagicMock(stdout=" M file.py\n")
        assert is_clean() is False


class TestGetDirtyFiles:
    @patch("regix.git._run_git")
    def test_modified_files(self, mock_run):
        # git status --porcelain: "XY filename"; note .strip() on full stdout
        mock_run.return_value = MagicMock(stdout="MM src/a.py\n?? src/new.py\n")
        files = get_dirty_files()
        names = {str(f) for f in files}
        assert "src/a.py" in names
        assert "src/new.py" in names

    @patch("regix.git._run_git")
    def test_no_dirty(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        files = get_dirty_files()
        assert files == []


class TestGetChangedFiles:
    @patch("regix.git._run_git")
    def test_changed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="a.py\nb.py\n")
        files = get_changed_files("HEAD~1", "HEAD")
        assert files == ["a.py", "b.py"]

    @patch("regix.git._run_git")
    def test_error_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        files = get_changed_files("bad", "refs")
        assert files == []


class TestReadLocalSources:
    def test_reads_files(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("hello", encoding="utf-8")
        (tmp_path / "b.py").write_text("world", encoding="utf-8")
        sources = read_local_sources(tmp_path, [Path("a.py"), Path("b.py")])
        assert sources == {"a.py": "hello", "b.py": "world"}

    def test_skips_missing(self, tmp_path: Path):
        sources = read_local_sources(tmp_path, [Path("missing.py")])
        assert sources == {}

    def test_skips_binary(self, tmp_path: Path):
        p = tmp_path / "binary.py"
        p.write_bytes(b"\xff\xfe" + b"\x00" * 100)
        sources = read_local_sources(tmp_path, [Path("binary.py")])
        # May read or skip depending on encoding — just shouldn't crash
        assert isinstance(sources, dict)


class TestListCommits:
    @patch("regix.git._run_git")
    def test_parses_log(self, mock_run):
        # git log format: sha\niso-date\nauthor\nsubject (4 lines per commit)
        mock_run.return_value = MagicMock(
            stdout="abc123\n2025-01-15T10:00:00+00:00\ntom\ninitial commit\ndef456\n2025-01-14T09:00:00+00:00\njane\nsecond\n"
        )
        commits = list_commits("HEAD", depth=2)
        assert len(commits) == 2
        assert commits[0].sha == "abc123"
        assert commits[0].author == "tom"
        assert commits[1].sha == "def456"

    @patch("regix.git._run_git")
    def test_empty_log(self, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        commits = list_commits("HEAD", depth=5)
        assert commits == []


class TestReadTreeSources:
    @patch("regix.git.resolve_ref", return_value="abc123")
    @patch("subprocess.run")
    def test_reads_tar(self, mock_subprocess, mock_resolve):
        import io
        import tarfile
        # Build a tar archive in memory
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            content = b"x = 1\n"
            info = tarfile.TarInfo(name="src/a.py")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
            # Add a non-.py file that should be skipped
            info2 = tarfile.TarInfo(name="README.md")
            info2.size = 5
            tar.addfile(info2, io.BytesIO(b"hello"))
        mock_subprocess.return_value = MagicMock(stdout=buf.getvalue())
        from regix.git import read_tree_sources
        sources = read_tree_sources("HEAD", Path("."))
        assert "src/a.py" in sources
        assert sources["src/a.py"] == "x = 1\n"
        assert "README.md" not in sources


class TestCommitInfo:
    def test_dataclass(self):
        from datetime import datetime
        ci = CommitInfo(sha="abc", timestamp=datetime.now(), author="tom", message="test")
        assert ci.sha == "abc"
        assert ci.author == "tom"
