"""Shared test fixtures — in-memory sources, pre-built configs and snapshots.

All fixtures use RAM-only data so tests never hit the network or

create temporary files on disk (unless explicitly needed via tmp_path).
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from regix.config import RegressionConfig
from regix.models import Snapshot, SymbolMetrics

SAMPLE_SOURCE_SIMPLE = 'import os\n\ndef greet(name):\n    """Say hello."""\n    return f"Hello, {name}!"\n\nclass Greeter:\n    """A greeter class."""\n    def __init__(self, prefix="Hi"):\n        self.prefix = prefix\n\n    def say(self, name):\n        """Say greeting."""\n        return f"{self.prefix}, {name}"\n'
SAMPLE_SOURCE_COMPLEX = 'import os\nimport sys\nfrom pathlib import Path\n\n\ndef compute(data, factor=1):\n    """Process data with nested logic."""\n    result = []\n    for item in data:\n        if item > 0:\n            for sub in range(item):\n                if sub % 2 == 0:\n                    result.append(sub * factor)\n                else:\n                    result.append(sub + factor)\n        else:\n            result.append(0)\n    return result\n\n\ndef transform(items):\n    total = 0\n    for item in items:\n        total += item\n    return total / len(items) if items else 0\n\n\nclass Handler:\n    def __init__(self, config):\n        self.config = config\n        self._cache = {}\n\n    def process(self, value):\n        if value in self._cache:\n            return self._cache[value]\n        result = self._compute(value)\n        self._cache[value] = result\n        return result\n\n    def _compute(self, value):\n        return value * 2 + 1\n'
SAMPLE_SOURCE_NO_DOCSTRINGS = 'def undocumented_a():\n    pass\n\ndef undocumented_b(x):\n    return x + 1\n\nclass Bare:\n    def method(self):\n        pass\n'

@pytest.fixture
def default_config() -> RegressionConfig:
    """Pre-built default config — no file I/O."""
    return RegressionConfig()

@pytest.fixture
def sample_sources() -> dict[str, str]:
    """In-memory source dict with 3 synthetic files."""
    return {'simple.py': SAMPLE_SOURCE_SIMPLE, 'complex.py': SAMPLE_SOURCE_COMPLEX, 'bare.py': SAMPLE_SOURCE_NO_DOCSTRINGS}

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
    return Snapshot(ref='HEAD', commit_sha='abc1234', timestamp=datetime.now(timezone.utc), workdir='.', symbols=symbols)

@pytest.fixture
def disk_sources(tmp_path: Path, sample_sources: dict[str, str]) -> tuple[Path, list[Path]]:
    """Write sample sources to tmp_path for backends that need disk.

    Returns (workdir, file_list).
    """
    files: list[Path] = []
    for name, content in sample_sources.items():
        p = tmp_path / name
        p.write_text(content, encoding='utf-8')
        files.append(Path(name))
    return (tmp_path, files)