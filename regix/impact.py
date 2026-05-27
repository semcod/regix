"""Dynamic Change-Impact and Targeted Test Selection Engine."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set


class ImpactAnalyzer:
    """Generic impact analyzer for local code changes and test suite mapping."""

    def __init__(self, workdir: str = "."):
        self.root = Path(workdir).resolve()
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

    def _fallback_yaml_parse(self, content: str) -> Dict[str, Any]:
        """Simple fallback YAML parser to avoid external dependencies in regix core."""
        data = {"context": "", "commands": [], "queries": [], "events": []}
        
        context_match = re.search(r'^context:\s*([\w-]+)', content, re.MULTILINE)
        if context_match:
            data["context"] = context_match.group(1)

        current_section = None
        current_item = {}
        
        for line in content.splitlines():
            if line.startswith("commands:"):
                current_section = "commands"
            elif line.startswith("queries:"):
                current_section = "queries"
            elif line.startswith("events:"):
                current_section = "events"
            elif line.strip().startswith("- name:"):
                if current_item and current_section:
                    data[current_section].append(current_item)
                name_match = re.search(r'name:\s*(\w+)', line)
                if name_match:
                    current_item = {"name": name_match.group(1), "source": {}}
            elif "file:" in line and current_item:
                file_match = re.search(r'file:\s*([\w/-]+\.\w+)', line)
                if file_match:
                    current_item["source"]["file"] = file_match.group(1)
            elif "class:" in line and current_item:
                class_match = re.search(r'class:\s*(\w+)', line)
                if class_match:
                    current_item["source"]["class"] = class_match.group(1)

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
            allowed_prefixes = ("backend/", "frontend/", "connect-", "packages/", "services/")
            ignored_substrings = (
                "/node_modules/", "/.venv/", "/__pycache__/", "/project/", "project/",
                "/batch_", "batch_", "/reports/", "reports/", "/redeploy/", "redeploy/"
            )
            
            filtered_files = []
            for f in files:
                # Must start with allowed prefix or be a main level config file
                if not any(f.startswith(p) for p in allowed_prefixes) and "/" in f:
                    continue
                # Must not contain ignored substrings
                if any(sub in f or f.startswith(sub) for sub in ignored_substrings):
                    continue
                filtered_files.append(f)
                
            return sorted(list(set(filtered_files)))
        except Exception:
            return []

    def analyze_impact(self, modified_files: List[str]) -> Dict[str, Any]:
        """Performs change-impact analysis and maps files to selective tests."""
        impacted_contexts: Set[str] = set()
        pytest_targets: Set[str] = set()
        testql_scenarios: Set[str] = set()
        visual_diff_routes: Set[str] = set()

        scenarios_dir = self.root / "testql-testing" / "scenarios"

        for file_path_str in modified_files:
            file_path = Path(file_path_str)
            relative_str = str(file_path)

            # 1. Folder structure-based context mapping
            context = None
            for part in file_path.parts:
                if part.startswith("connect-"):
                    context = part
                    break
            if context:
                impacted_contexts.add(context)

            # 2. SWOP manifest-based mapping
            for src_file, info in self.dependency_graph.items():
                if src_file in relative_str or relative_str in src_file:
                    impacted_contexts.add(info["context"])
                    if info["class"]:
                        pytest_targets.add(f"backend/tests/ -k {info['class']}")

            # 3. Python unit test mapping
            if "backend" in file_path.parts or file_path.suffix == ".py":
                stem = file_path.stem
                potential_tests = [
                    self.root / "backend" / "tests" / f"test_{stem}.py",
                    self.root / "tests" / f"test_{stem}.py"
                ]
                for p_test in potential_tests:
                    if p_test.exists():
                        pytest_targets.add(str(p_test.relative_to(self.root)))

            # 4. Frontend visual route mapping
            if "frontend" in file_path.parts and file_path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
                route_match = re.search(r'connect-([\w-]+)', relative_str)
                if route_match:
                    route = f"/{route_match.group(0)}"
                    visual_diff_routes.add(route)

        # 5. Scenarios matching impacted contexts
        if scenarios_dir.exists():
            for context in impacted_contexts:
                for scenario in scenarios_dir.glob(f"*{context}*.testql.toon.yaml"):
                    testql_scenarios.add(str(scenario.relative_to(self.root)))
                visual_diff_routes.add(f"/{context}")

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
