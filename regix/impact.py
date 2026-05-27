"""Dynamic Change-Impact and Targeted Test Selection Engine."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set


class ImpactAnalyzer:
    """Generic impact analyzer for local code changes and test suite mapping."""

    def __init__(self, workdir: str = ".", config: RegressionConfig | None = None):
        self.root = Path(workdir).resolve()
        if config is None:
            from regix.config import RegressionConfig
            self.config = RegressionConfig()
        else:
            self.config = config
        self.dependency_graph: Dict[str, Dict[str, Any]] = {}
        self._load_swop_mappings()

    def _load_swop_mappings(self):
        """Loads CQRS and SWOP mappings if present in the workspace."""
        manifests_dir = self.root / ".swop" / "manifests"
        if not manifests_dir.exists():
            return

        try:
            import yaml
        except ImportError:
            yaml = None

        for manifest_file in manifests_dir.glob("**/*.yml"):
            try:
                content = manifest_file.read_text(encoding="utf-8")
                if yaml:
                    data = yaml.safe_load(content)
                else:
                    data = self._fallback_yaml_parse(content)

                if not data:
                    continue

                context = data.get("context", "")
                
                # Check commands, queries, events
                items = data.get("commands", []) + data.get("queries", []) + data.get("events", [])
                for item in items:
                    name = item.get("name")
                    source = item.get("source", {})
                    source_file = source.get("file")
                    if source_file:
                        self.dependency_graph[source_file] = {
                            "context": context,
                            "name": name,
                            "class": source.get("class"),
                            "emits": item.get("emits", [])
                        }
            except Exception:
                pass

    def _parse_yaml_section_header(self, line: str) -> str | None:
        """Parse YAML section header. Returns section name or None."""
        if line.startswith("commands:"):
            return "commands"
        elif line.startswith("queries:"):
            return "queries"
        elif line.startswith("events:"):
            return "events"
        return None

    def _parse_yaml_item_start(self, line: str) -> dict[str, Any] | None:
        """Parse start of a YAML item. Returns new item dict or None."""
        name_match = re.search(r'name:\s*(\w+)', line)
        if name_match:
            return {"name": name_match.group(1), "source": {}}
        return None

    def _parse_yaml_item_field(self, line: str, item: dict[str, Any]) -> None:
        """Parse a YAML item field and update item dict."""
        if "file:" in line:
            file_match = re.search(r'file:\s*([\w/-]+\.\w+)', line)
            if file_match:
                item["source"]["file"] = file_match.group(1)
        elif "class:" in line:
            class_match = re.search(r'class:\s*(\w+)', line)
            if class_match:
                item["source"]["class"] = class_match.group(1)

    def _fallback_yaml_parse(self, content: str) -> Dict[str, Any]:
        """Simple fallback YAML parser to avoid external dependencies in regix core."""
        data = {"context": "", "commands": [], "queries": [], "events": []}
        
        context_match = re.search(r'^context:\s*([\w-]+)', content, re.MULTILINE)
        if context_match:
            data["context"] = context_match.group(1)

        current_section = None
        current_item: Dict[str, Any] = {}
        
        for line in content.splitlines():
            section = self._parse_yaml_section_header(line)
            if section:
                current_section = section
            elif line.strip().startswith("- name:"):
                if current_item and current_section:
                    data[current_section].append(current_item)
                new_item = self._parse_yaml_item_start(line)
                if new_item:
                    current_item = new_item
            elif current_item:
                self._parse_yaml_item_field(line, current_item)

        if current_item and current_section:
            data[current_section].append(current_item)

        return data

    def get_git_modified_files(self) -> List[str]:
        """Detects changed, added, and untracked files in git workspace."""
        try:
            res = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True, text=True, check=True, cwd=str(self.root)
            )
            res_untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True, text=True, check=True, cwd=str(self.root)
            )
            files = [line.strip() for line in (res.stdout + res_untracked.stdout).splitlines() if line.strip()]
            
            # Filter to focus only on active code paths and ignore massive temp/build/artifact directories
            allowed_prefixes = tuple(self.config.impact_include_prefixes)
            ignored_globs = self.config.impact_ignore_globs
            
            filtered_files = []
            for f in files:
                # Must start with allowed prefix or be a main level config file
                if allowed_prefixes and not any(f.startswith(p) for p in allowed_prefixes) and "/" in f:
                    continue
                # Must not match ignored globs
                import fnmatch
                if any(fnmatch.fnmatch(f, glob) for glob in ignored_globs):
                    continue
                filtered_files.append(f)
                
            return sorted(list(set(filtered_files)))
        except Exception:
            return []

    def _map_folder_to_context(self, file_path: Path) -> str | None:
        """Extract context from folder structure. Returns context or None."""
        for part in file_path.parts:
            if part.startswith("connect-"):
                return part
        return None

    def _map_swop_manifest(self, relative_str: str) -> tuple[Set[str], Set[str]]:
        """Map file to SWOP manifest contexts and pytest targets. Returns (contexts, targets)."""
        contexts: Set[str] = set()
        targets: Set[str] = set()
        for src_file, info in self.dependency_graph.items():
            if src_file in relative_str or relative_str in src_file:
                contexts.add(info["context"])
                if info["class"]:
                    targets.add(f"backend/tests/ -k {info['class']}")
        return contexts, targets

    def _map_python_unit_tests(self, file_path: Path) -> Set[str]:
        """Map Python file to unit test targets using configured patterns."""
        targets: Set[str] = set()
        if file_path.suffix != ".py":
            return targets

        stem = file_path.stem
        try:
            rel_dir = str(file_path.parent.relative_to(self.root))
            if rel_dir == ".":
                rel_dir = ""
        except ValueError:
            rel_dir = ""

        for pattern in self.config.impact_test_patterns:
            p_str = pattern.replace("{stem}", stem).replace("{dir}", rel_dir)
            p_str = p_str.replace("//", "/").lstrip("/")
            p_test = self.root / p_str
            if p_test.exists():
                targets.add(str(p_test.relative_to(self.root)))
        return targets

    def _map_frontend_routes(self, file_path: Path) -> Set[str]:
        """Map frontend file to visual diff routes. Returns set of routes."""
        routes: Set[str] = set()
        if "frontend" in file_path.parts and file_path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
            relative_str = str(file_path)
            route_match = re.search(r'connect-([\w-]+)', relative_str)
            if route_match:
                route = f"/{route_match.group(0)}"
                routes.add(route)
        return routes

    def _map_scenarios(self, impacted_contexts: Set[str]) -> tuple[Set[str], Set[str]]:
        """Map contexts to testql scenarios and visual routes. Returns (scenarios, routes)."""
        scenarios: Set[str] = set()
        routes: Set[str] = set()
        scenarios_dir = self.root / "testql-testing" / "scenarios"
        if scenarios_dir.exists():
            for context in impacted_contexts:
                for scenario in scenarios_dir.glob(f"*{context}*.testql.toon.yaml"):
                    scenarios.add(str(scenario.relative_to(self.root)))
                routes.add(f"/{context}")
        return scenarios, routes

    def analyze_impact(self, modified_files: List[str]) -> Dict[str, Any]:
        """Performs change-impact analysis and maps files to selective tests."""
        impacted_contexts: Set[str] = set()
        pytest_targets: Set[str] = set()
        testql_scenarios: Set[str] = set()
        visual_diff_routes: Set[str] = set()

        for file_path_str in modified_files:
            file_path = Path(file_path_str)
            relative_str = str(file_path)

            context = self._map_folder_to_context(file_path)
            if context:
                impacted_contexts.add(context)

            swop_contexts, swop_targets = self._map_swop_manifest(relative_str)
            impacted_contexts.update(swop_contexts)
            pytest_targets.update(swop_targets)

            pytest_targets.update(self._map_python_unit_tests(file_path))
            visual_diff_routes.update(self._map_frontend_routes(file_path))

        scenarios, scenario_routes = self._map_scenarios(impacted_contexts)
        testql_scenarios.update(scenarios)
        visual_diff_routes.update(scenario_routes)

        return {
            "modified_files": modified_files,
            "impacted_contexts": sorted(list(impacted_contexts)),
            "pytest_targets": sorted(list(pytest_targets)),
            "testql_scenarios": sorted(list(testql_scenarios)),
            "visual_diff_routes": sorted(list(visual_diff_routes)),
        }

    def execute_targeted_tests(self, analysis: Dict[str, Any], dry_run: bool = False, pytest_only: bool = False) -> Dict[str, Any]:
        """Runs the matched targeted test suites selectively."""
        results = {"pytest": [], "testql": []}

        for target in analysis["pytest_targets"]:
            cmd = ["pytest", target]
            if dry_run:
                results["pytest"].append({"command": " ".join(cmd), "status": "DRY_RUN"})
            else:
                res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root))
                status = "PASS" if res.returncode == 0 else "FAIL"
                results["pytest"].append({
                    "command": " ".join(cmd),
                    "status": status,
                    "stdout": res.stdout[:500],
                    "stderr": res.stderr[:500] if res.stderr else ""
                })

        if pytest_only:
            return results

        for scenario in analysis["testql_scenarios"]:
            cmd = ["python3", "-m", "testql", "run", scenario]
            if dry_run:
                results["testql"].append({"command": " ".join(cmd), "status": "DRY_RUN"})
            else:
                res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root))
                status = "PASS" if res.returncode == 0 else "FAIL"
                results["testql"].append({
                    "command": " ".join(cmd),
                    "status": status,
                    "stdout": res.stdout[:500],
                    "stderr": res.stderr[:500] if res.stderr else ""
                })

        return results
