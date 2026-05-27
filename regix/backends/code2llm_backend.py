"""Code2llm backend — parses code2llm TOON YAML output for rich AST metrics.

This backend runs code2llm (if needed) and parses the generated toon.yaml files
to extract per-symbol metrics including:
  - cyclomatic_complexity (CC)
  - fan_out / fan_in
  - line counts
  - function signatures and exports

This replaces the need for custom AST analyzers by leveraging code2llm's
comprehensive static analysis.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


from regix.backends.base import BackendBase, register_backend
from regix.config import RegressionConfig
from regix.models import SymbolMetrics


# Regex patterns for parsing code2llm header stats
_HEADER_STATS_RE = re.compile(
    r"^#\s+stats:\s+(?P<funcs>\d+)\s+func.*CC̄=(?P<avg_cc>[\d.]+)"
)
_FUNCTION_RE = re.compile(
    r"^(?P<name>[a-zA-Z_][a-zA-Z0-9_\.]*)\s*\([^)]*\)(?:\s*#.*CC=(?P<cc>\d+))?"
)
_EXPORT_LINE_RE = re.compile(
    r"^\s+(?P<symbol>[a-zA-Z_][a-zA-Z0-9_\.]*)\s*\([^)]*\)(?:\s*#.*CC=(?P<cc>\d+))?"
)


class Code2llmBackend(BackendBase):
    """Code2llm TOON YAML parser for rich structural metrics.

    Generates metrics from code2llm output:
      - cyclomatic_complexity per function
      - fan_out / fan_in from call graphs
      - line counts and symbol counts
      - export signatures
    """

    name = "code2llm"
    required_binary = "code2llm"

    def is_available(self) -> bool:
        """True when code2llm is on PATH."""
        return shutil.which("code2llm") is not None

    def version(self) -> str:
        """Return code2llm version."""
        try:
            result = subprocess.run(
                ["code2llm", "-h"],
                capture_output=True, text=True, check=False,
            )
            # Parse version from help output or use package info
            return "installed"
        except FileNotFoundError:
            return "not installed"

    def _run_code2llm(self, workdir: Path) -> Path:
        """Run code2llm to generate toon.yaml files, return output directory."""
        output_dir = workdir / ".code2llm_cache"
        output_dir.mkdir(exist_ok=True)

        # Check if recent output exists (less than 1 hour old)
        map_file = output_dir / "map.toon.yaml"
        if map_file.exists():
            import time
            age_hours = (time.time() - map_file.stat().st_mtime) / 3600
            if age_hours < 1:
                return output_dir

        try:
            subprocess.run(
                ["code2llm", str(workdir), "-f", "toon", "-o", str(output_dir)],
                capture_output=True, check=False, cwd=str(workdir),
            )
        except (subprocess.SubprocessError, OSError):
            pass

        return output_dir

    def _parse_header_stats(self, content: str) -> dict:
        """Parse header stats from toon content."""
        stats = {}
        for line in content.splitlines()[:10]:
            match = _HEADER_STATS_RE.match(line)
            if match:
                stats["total_functions"] = int(match.group("funcs"))
                stats["avg_cc"] = float(match.group("avg_cc"))
        return stats

    def _parse_module_list_entry(self, line: str) -> tuple[str | None, int | None]:
        """Parse a module list entry line. Returns (file, line_count) or (None, None)."""
        parts = line.strip().split(",")
        if len(parts) == 2 and parts[1].strip().isdigit():
            return parts[0], int(parts[1])
        return None, None

    def _parse_function_entry(self, line: str, current_file: str) -> SymbolMetrics | None:
        """Parse a function entry line. Returns SymbolMetrics or None."""
        stripped = line.strip()
        match = _FUNCTION_RE.match(stripped)
        if match:
            symbol_name = match.group("name")
            cc_str = match.group("cc")
            cc = int(cc_str) if cc_str else None
            return SymbolMetrics(
                file=current_file,
                symbol=symbol_name,
                cc=cc,
                raw={"code2llm_cc": cc} if cc else {},
            )
        return None

    def _parse_map_toon(self, map_file: Path) -> tuple[dict, list[SymbolMetrics]]:
        """Parse map.toon.yaml and extract file-level and symbol metrics."""
        results: list[SymbolMetrics] = []

        if not map_file.exists():
            return {}, results

        try:
            content = map_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return {}, results

        global_stats = self._parse_header_stats(content)

        current_file = None
        in_details = False
        lines = content.splitlines()

        for line in lines:
            if line.startswith("M["):
                continue

            if not in_details and line.startswith("  ") and "," in line:
                file_path, line_count = self._parse_module_list_entry(line)
                if file_path and line_count is not None:
                    current_file = file_path
                    results.append(SymbolMetrics(
                        file=current_file,
                        symbol=None,
                        length=line_count,
                        raw={"code2llm_lines": line_count},
                    ))

            if line == "D:":
                in_details = True
                continue

            if in_details and line.endswith(":") and not line.startswith(" "):
                current_file = line.rstrip(":")
                continue

            if in_details and current_file and line.startswith("    "):
                func_metrics = self._parse_function_entry(line, current_file)
                if func_metrics:
                    results.append(func_metrics)

            if in_details and current_file and "e:" in line:
                continue

        return global_stats, results

    def _parse_next_action_line(self, line: str) -> tuple[str | None, str | None]:
        """Parse a NEXT action line. Returns (action, target) or (None, None)."""
        match = re.search(r"\[\d+\]\s+!!?\s+(\w+)\s+(.+)", line)
        if match:
            return match.groups()
        return None, None

    def _parse_cc_from_line(self, line: str) -> int | None:
        """Extract CC value from a line. Returns CC or None."""
        cc_match = re.search(r"CC=(\d+)", line)
        if cc_match:
            return int(cc_match.group(1))
        return None

    def _parse_target_to_symbol_file(self, target: str) -> tuple[str | None, str | None]:
        """Parse target string into (symbol, file_path). Returns (None, None) if invalid."""
        if " " in target:
            parts = target.split()
            if len(parts) >= 2:
                return parts[0], parts[1]
        return None, None

    def _parse_evolution_toon(self, evo_file: Path) -> list[SymbolMetrics]:
        """Parse evolution.toon.yaml for complexity alerts and hotspots."""
        results: list[SymbolMetrics] = []

        if not evo_file.exists():
            return results

        try:
            content = evo_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return results

        in_next = False
        current_item: dict[str, str] = {}

        for line in content.splitlines():
            if line.startswith("NEXT["):
                in_next = True
                continue
            if in_next and not line.strip():
                in_next = False
                continue

            if in_next and line.strip().startswith("["):
                action, target = self._parse_next_action_line(line)
                if action and target:
                    current_item = {"action": action, "target": target.strip()}

            if in_next and "CC=" in line:
                cc = self._parse_cc_from_line(line)
                if cc and current_item.get("target"):
                    symbol, file_path = self._parse_target_to_symbol_file(current_item["target"])
                    if symbol and file_path:
                        results.append(SymbolMetrics(
                            file=file_path,
                            symbol=symbol,
                            cc=cc,
                            raw={
                                "code2llm_recommended_action": current_item.get("action"),
                                "code2llm_cc": cc,
                            },
                        ))

        return results

    def collect(
        self,
        workdir: Path,
        files: list[Path],
        config: RegressionConfig,
        sources: dict[str, str] | None = None,
    ) -> list[SymbolMetrics]:
        """Collect metrics from code2llm toon.yaml output."""
        # Run or use cached code2llm output
        output_dir = self._run_code2llm(workdir)

        all_results: list[SymbolMetrics] = []

        # Parse map.toon.yaml for structural metrics
        map_file = output_dir / "map.toon.yaml"
        _, map_results = self._parse_map_toon(map_file)
        all_results.extend(map_results)

        # Parse evolution.toon.yaml for complexity recommendations
        evo_file = output_dir / "evolution.toon.yaml"
        evo_results = self._parse_evolution_toon(evo_file)

        # Merge evolution data with map data
        for evo in evo_results:
            found = False
            for existing in all_results:
                if (existing.file == evo.file and existing.symbol == evo.symbol):
                    # Update with evolution data
                    if evo.cyclomatic_complexity:
                        existing.cyclomatic_complexity = evo.cyclomatic_complexity
                    existing.raw.update(evo.raw)
                    found = True
                    break
            if not found:
                all_results.append(evo)

        # Filter to requested files if specified
        if files:
            file_set = {str(f) for f in files}
            all_results = [r for r in all_results if r.file in file_set]

        return all_results


register_backend(Code2llmBackend())
