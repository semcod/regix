"""Coverage backend — reads pytest-cov .coverage data."""

from __future__ import annotations

import json
from pathlib import Path

from regix.backends import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics


class CoverageBackend(BackendBase):
    name = "coverage"
    required_binary = None

    def is_available(self) -> bool:
        try:
            import coverage as cov  # noqa: F401
            return True
        except ImportError:
            return False

    def version(self) -> str:
        try:
            import coverage
            return coverage.__version__
        except (ImportError, AttributeError):
            return "not installed"

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
    ) -> list[SymbolMetrics]:
        """Read coverage from a JSON report or .coverage file."""
        results: list[SymbolMetrics] = []

        # Try JSON report first (from pytest --cov-report=json)
        json_candidates = [
            workdir / ".regix" / "coverage.json",
            workdir / "coverage.json",
            workdir / "htmlcov" / "status.json",
        ]
        for cj in json_candidates:
            if cj.exists():
                return self._from_json(cj, files)

        # Fallback: read .coverage SQLite via coverage API
        cov_file = workdir / ".coverage"
        if cov_file.exists():
            return self._from_coverage_file(cov_file, files, workdir)

        return results

    def _from_json(
        self, path: Path, files: list[Path]
    ) -> list[SymbolMetrics]:
        results: list[SymbolMetrics] = []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return results

        file_data = data.get("files", {})
        file_set = {str(f) for f in files}
        for fname, finfo in file_data.items():
            if file_set and fname not in file_set:
                continue
            summary = finfo.get("summary", {})
            pct = summary.get("percent_covered", None)
            if pct is not None:
                results.append(
                    SymbolMetrics(
                        file=fname,
                        symbol=None,
                        coverage=pct,
                        raw={"covered_lines": summary.get("covered_lines", 0)},
                    )
                )
        return results

    def _from_coverage_file(
        self, cov_path: Path, files: list[Path], workdir: Path
    ) -> list[SymbolMetrics]:
        results: list[SymbolMetrics] = []
        try:
            import coverage as cov_lib

            cov = cov_lib.Coverage(data_file=str(cov_path))
            cov.load()
            data = cov.get_data()
            for fname in data.measured_files():
                lines = data.lines(fname) or []
                missing = data.lines(fname)  # simplified
                total = len(lines)
                if total > 0:
                    pct = (len(lines) / total) * 100
                else:
                    pct = 0.0
                results.append(
                    SymbolMetrics(file=fname, symbol=None, coverage=pct)
                )
        except Exception:
            pass
        return results


register_backend(CoverageBackend())
