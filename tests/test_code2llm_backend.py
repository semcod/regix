"""Tests for code2llm backend."""

from __future__ import annotations

from pathlib import Path

import pytest

from regix.backends.code2llm_backend import Code2llmBackend, _HEADER_STATS_RE
from regix.config import RegressionConfig


class TestCode2llmBackend:
    """Tests for Code2llmBackend parser."""

    def test_header_stats_regex(self):
        """Test parsing of code2llm header stats line."""
        line = "# stats: 166 func | 0 cls | 25 mod | CC̄=4.6 | critical:7 | cycles:0"
        match = _HEADER_STATS_RE.match(line)
        assert match is not None
        assert match.group("funcs") == "166"
        assert match.group("avg_cc") == "4.6"

    def test_backend_name(self):
        """Test backend name is correctly set."""
        backend = Code2llmBackend()
        assert backend.name == "code2llm"

    def test_backend_availability(self):
        """Test backend availability check (may be True or False depending on environment)."""
        backend = Code2llmBackend()
        # Just verify the method runs without error
        available = backend.is_available()
        assert isinstance(available, bool)

    def test_parse_map_toon_with_existing_file(self):
        """Test parsing with the project's own map.toon.yaml."""
        backend = Code2llmBackend()
        map_file = Path("project/map.toon.yaml")

        if not map_file.exists():
            pytest.skip("map.toon.yaml not found")

        global_stats, results = backend._parse_map_toon(map_file)

        # Verify we got some stats
        assert "total_functions" in global_stats
        assert "avg_cc" in global_stats

        # Verify we got results
        assert len(results) > 0

        # Check file-level entries (symbol=None)
        file_entries = [r for r in results if r.symbol is None]
        assert len(file_entries) > 0

        # Each file entry should have a length
        for entry in file_entries:
            assert entry.file is not None
            assert entry.length is not None
            assert entry.length > 0

    def test_parse_evolution_toon_with_existing_file(self):
        """Test parsing evolution.toon.yaml for complexity recommendations."""
        backend = Code2llmBackend()
        evo_file = Path("project/evolution.toon.yaml")

        if not evo_file.exists():
            pytest.skip("evolution.toon.yaml not found")

        results = backend._parse_evolution_toon(evo_file)

        # Results may be empty if no high-complexity functions
        # but parsing should not error
        for r in results:
            assert r.file is not None
            assert r.symbol is not None
            assert r.cc is not None

    def test_collect_uses_cache(self, tmp_path: Path):
        """Test that collect() uses cached output when available."""
        backend = Code2llmBackend()
        cache_dir = tmp_path / ".code2llm_cache"
        cache_dir.mkdir()

        # Create a dummy map.toon.yaml
        dummy_map = cache_dir / "map.toon.yaml"
        dummy_map.write_text("""# regix | 2f 100L | python:2 | 2026-01-01
# stats: 10 func | 0 cls | 2 mod | CC̄=3.5 | critical:0 | cycles:0
# Keys: M=modules, D=details
M[2]:
  test.py,50
  other.py,50
D:
  test.py:
    e: test_func
    test_func()  # CC=5
""")

        # Create dummy evolution.toon.yaml
        dummy_evo = cache_dir / "evolution.toon.yaml"
        dummy_evo.write_text("""# code2llm/evolution | 10 func | 2f | 2026-01-01

NEXT[0]:

RISKS[0]:

METRICS-TARGET:
  CC̄: 3.5 → ≤3.2
""")

        # Monkey-patch _run_code2llm to return our cache dir
        original_run = backend._run_code2llm
        backend._run_code2llm = lambda workdir: cache_dir

        try:
            config = RegressionConfig()
            results = backend.collect(tmp_path, [], config)

            # Should have file entries from the cached map
            assert len(results) > 0

        finally:
            backend._run_code2llm = original_run
