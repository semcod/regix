from pathlib import Path
from regix.models import SymbolMetrics


class Code2llmBackend(BackendBase):
    """Code2llm TOON YAML parser for rich structural metrics.

    Generates metrics from code2llm output:
      - cyclomatic_complexity per function
      - fan_out / fan_in from call graphs
      - line counts and symbol ..."""

    def is_available(self) -> bool:
        """True when code2llm is on PATH."""
        return shutil.which("code2llm") is not None

    def version(self) -> str:
        """Return code2llm version."""
        try:
            result = subprocess.run(
                ["code2llm", "-h"],
                capture_output=True,
                text=True,
                check=False,
            )
            return "installed"
        except FileNotFoundError:
            return "not installed"

    def _parse_map_toon(self, map_file: Path) -> tuple[dict, list[SymbolMetrics]]:
        """Parse map.toon.yaml and extract file-level and symbol metrics."""
        results: list[SymbolMetrics] = []
        global_stats = {}

        if not map_file.exists():
            return global_stats, results

        try:
            content = map_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return global_stats, results

        self._parse_header_stats(content, global_stats)
        self._parse_module_list(content, results)

        return global_stats, results

    def _parse_header_stats(self, content: str, global_stats: dict) -> None:
        """Parse header stats from the content."""
        for line in content.splitlines()[:10]:
            match = _HEADER_STATS_RE.match(line)
            if match:
                global_stats["total_functions"] = int(match.group("funcs"))
                global_stats["avg_cc"] = float(match.group("avg_cc"))

    def _parse_module_list(self, content: str, results: list[SymbolMetrics]) -> None:
        """Parse module list and details from the content."""
        current_file = None
        in_details = False
        lines = content.splitlines()

        for i, line in enumerate(lines):
            if line.startswith("M["):
                continue

            if not in_details and line.startswith("  ") and "," in line:
                self._parse_file_entry(line, results)

            if line == "D:":
                in_details = True
                continue

            if in_details:
                if line.endswith(":") and not line.startswith(" "):
                    current_file = line.rstrip(":")
                    continue

                if current_file and line.startswith("    "):
                    self._parse_function_entry(line, current_file, results)

                if current_file and "e:" in line:
                    # Extract fan-out from exports section
                    continue

    def _parse_file_entry(self, line: str, results: list[SymbolMetrics]) -> None:
        """Parse a file entry from the module list."""
        parts = line.strip().split(",")
        if len(parts) == 2 and parts[1].strip().isdigit():
            current_file = parts[0]
            line_count = int(parts[1])
            results.append(
                SymbolMetrics(
                    file=current_file,
                    symbol=None,
                    length=line_count,
                    raw={"code2llm_lines": line_count},
                )
            )

    def _parse_function_entry(
        self, line: str, current_file: str, results: list[SymbolMetrics]
    ) -> None:
        """Parse a function entry from the details section."""
        stripped = line.strip()
        match = _FUNCTION_RE.match(stripped)
        if match:
            symbol_name = match.group("name")
            cc_str = match.group("cc")
            cc = int(cc_str) if cc_str else None

            results.append(
                SymbolMetrics(
                    file=current_file,
                    symbol=symbol_name,
                    cc=cc,
                    raw={"code2llm_cc": cc} if cc else {},
                )
            )
