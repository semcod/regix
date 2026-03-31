"""Shared test fixtures — in-memory sources, pre-built configs and snapshots.

All fixtures use RAM-only data so tests never hit the network or
create temporary files on disk (unless explicitly needed via tmp_path).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from regix.config import RegressionConfig
from regix.models import Snapshot, SymbolMetrics


# ── Reusable source code snippets ──────────────────────────────────────────

SAMPLE_SOURCE_SIMPLE = '''\
import os

def greet(name):
    """Say hello."""
    return f"Hello, {name}!"

class Greeter:
    """A greeter class."""
    def __init__(self, prefix="Hi"):
        self.prefix = prefix

    def say(self, name):
        """Say greeting."""
        return f"{self.prefix}, {name}"
'''

SAMPLE_SOURCE_COMPLEX = '''\
import os
import sys
from pathlib import Path


def compute(data, factor=1):
    """Process data with nested logic."""
    result = []
    for item in data:
        if item > 0:
            for sub in range(item):
                if sub % 2 == 0:
                    result.append(sub * factor)
                else:
                    result.append(sub + factor)
        else:
            result.append(0)
    return result


def transform(items):
    total = 0
    for item in items:
        total += item
    return total / len(items) if items else 0


class Handler:
    def __init__(self, config):
        self.config = config
        self._cache = {}

    def process(self, value):
        if value in self._cache:
            return self._cache[value]
        result = self._compute(value)
        self._cache[value] = result
        return result

    def _compute(self, value):
        return value * 2 + 1
'''

SAMPLE_SOURCE_NO_DOCSTRINGS = '''\
def undocumented_a():
    pass

def undocumented_b(x):
    return x + 1

class Bare:
    def method(self):
        pass
'''


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def default_config() -> RegressionConfig:
    """Pre-built default config — no file I/O."""
    return RegressionConfig()


@pytest.fixture
def sample_sources() -> dict[str, str]:
    """In-memory source dict with 3 synthetic files."""
    return {
        "simple.py": SAMPLE_SOURCE_SIMPLE,
        "complex.py": SAMPLE_SOURCE_COMPLEX,
        "bare.py": SAMPLE_SOURCE_NO_DOCSTRINGS,
    }


@pytest.fixture
def sample_files(sample_sources: dict[str, str]) -> list[Path]:
    """File list matching sample_sources keys."""
    return [Path(k) for k in sample_sources]


@pytest.fixture
def sample_snapshot(sample_sources: dict[str, str]) -> Snapshot:
    """A Snapshot built entirely in RAM from sample sources."""
    symbols = []
    for fname in sample_sources:
        symbols.append(SymbolMetrics(file=fname, symbol=None, cc=5, mi=50.0))
    return Snapshot(
        ref="HEAD",
        commit_sha="abc1234",
        timestamp=datetime.now(timezone.utc),
        workdir=".",
        symbols=symbols,
    )


@pytest.fixture
def disk_sources(tmp_path: Path, sample_sources: dict[str, str]) -> tuple[Path, list[Path]]:
    """Write sample sources to tmp_path for backends that need disk.

    Returns (workdir, file_list).
    """
    files: list[Path] = []
    for name, content in sample_sources.items():
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        files.append(Path(name))
    return tmp_path, files
