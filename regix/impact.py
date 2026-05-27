"""Dynamic Change-Impact and Targeted Test Selection Engine."""

from __future__ import annotations

import ast
import fnmatch
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set

from regix.config import RegressionConfig


class ImpactAnalyzer:
    """Generic impact analyzer for local code changes and test suite mapping."""

    def __init__(self, workdir: str = ".", config: RegressionConfig | None = None):
        self.root = Path(workdir).resolve()
        if config is None:
            try:
                cfg = RegressionConfig.from_file(self.root)
            except FileNotFoundError:
                cfg = RegressionConfig()
            cfg.workdir = str(self.root)
            cfg.apply_env_overrides()
            self.config = cfg
        else:
            self.config = config
        self.dependency_graph: Dict[str, Dict[str, Any]] = {}
        self.module_to_file: Dict[str, str] = {}
        self.file_to_module: Dict[str, str] = {}
        self.import_graph: Dict[str, Set[str]] = {}
        self.reverse_import_graph: Dict[str, Set[str]] = {}
        self._import_graph_built = False
        self._load_swop_mappings()

    def _is_ignored_path(self, path: str) -> bool:
        """Return True if path matches any configured impact ignore glob."""
        normalized = path.replace("\\", "/")
        return any(fnmatch.fnmatch(normalized, pattern) for pattern in self.config.impact_ignore_globs)

    def _is_allowed_path(self, path: str) -> bool:
        """Return True if path is within configured include prefixes or prefixes are empty."""
        normalized = path.replace("\\", "/")
        prefixes = self.config.impact_include_prefixes
        if not prefixes:
            return True
        return any(normalized.startswith(prefix) for prefix in prefixes)

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
            
            filtered_files = []
            for f in files:
                if not self._is_allowed_path(f):
                    continue
                if self._is_ignored_path(f):
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
        rel_dir = "" if str(file_path.parent) == "." else str(file_path.parent)

        for pattern in self.config.impact_test_patterns:
            p_str = pattern.replace("{stem}", stem).replace("{dir}", rel_dir)
            p_str = p_str.replace("//", "/").lstrip("/")
            p_test = self.root / p_str
            if p_test.exists():
                targets.add(str(p_test.relative_to(self.root)))
        return targets

    def _module_name_from_relpath(self, rel_path: Path) -> str:
        """Convert a relative Python file path to an importable module name."""
        no_ext = rel_path.with_suffix("")
        parts = list(no_ext.parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def _extract_imports(self, module_name: str, source: str) -> Set[str]:
        """Extract import targets from a Python module source."""
        imports: Set[str] = set()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return imports

        module_parts = module_name.split(".") if module_name else []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level > 0:
                    anchor = module_parts[: max(0, len(module_parts) - node.level)]
                    rel_mod = ".".join([*anchor, base]) if base else ".".join(anchor)
                    if rel_mod:
                        imports.add(rel_mod)
                elif base:
                    imports.add(base)
        return imports

    def _resolve_local_import(self, import_name: str) -> str | None:
        """Resolve import path to a known local module if possible."""
        candidate = import_name
        while candidate:
            if candidate in self.module_to_file:
                return candidate
            if "." not in candidate:
                break
            candidate = candidate.rsplit(".", 1)[0]
        return None

    def _discover_python_files(self) -> List[Path]:
        """Discover Python files eligible for import-graph analysis."""
        import os

        files: List[Path] = []
        for root, dirs, filenames in os.walk(self.root, topdown=True):
            rel_root = Path(root).relative_to(self.root)
            pruned_dirs = []
            for d in dirs:
                rel = (rel_root / d) if str(rel_root) != "." else Path(d)
                rel_str = str(rel).replace("\\", "/")
                if self._is_ignored_path(rel_str):
                    continue
                pruned_dirs.append(d)
            dirs[:] = pruned_dirs

            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                rel = (rel_root / filename) if str(rel_root) != "." else Path(filename)
                rel_str = str(rel).replace("\\", "/")
                if self._is_ignored_path(rel_str):
                    continue
                if not self._is_allowed_path(rel_str):
                    continue
                files.append(rel)
        return files

    def _build_import_graph(self) -> None:
        """Build local module import graph and its reverse index."""
        if self._import_graph_built:
            return

        py_files = self._discover_python_files()
        self.module_to_file.clear()
        self.file_to_module.clear()
        self.import_graph.clear()
        self.reverse_import_graph.clear()

        for rel_path in py_files:
            module_name = self._module_name_from_relpath(rel_path)
            if not module_name:
                continue
            rel_str = str(rel_path).replace("\\", "/")
            self.module_to_file[module_name] = rel_str
            self.file_to_module[rel_str] = module_name

        for module_name, file_path in self.module_to_file.items():
            source_path = self.root / file_path
            try:
                source = source_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                self.import_graph[module_name] = set()
                continue

            imports = self._extract_imports(module_name, source)
            local_imports = {
                local
                for imp in imports
                if (local := self._resolve_local_import(imp)) is not None
            }
            self.import_graph[module_name] = local_imports

        for module_name, imports in self.import_graph.items():
            for imported in imports:
                self.reverse_import_graph.setdefault(imported, set()).add(module_name)

        self._import_graph_built = True

    def _collect_transitive_dependents(self, changed_modules: Set[str]) -> Set[str]:
        """Return modules that transitively depend on changed modules."""
        self._build_import_graph()
        if not changed_modules:
            return set()

        max_depth = max(1, int(self.config.impact_transitive_depth))
        visited: Set[str] = set(changed_modules)
        frontier: Set[str] = set(changed_modules)
        dependents: Set[str] = set()

        for _ in range(max_depth):
            next_frontier: Set[str] = set()
            for mod in frontier:
                for dep in self.reverse_import_graph.get(mod, set()):
                    if dep in visited:
                        continue
                    visited.add(dep)
                    dependents.add(dep)
                    next_frontier.add(dep)
            if not next_frontier:
                break
            frontier = next_frontier

        return dependents

    def _is_test_file(self, file_path: str) -> bool:
        """Return True for file paths that represent tests."""
        p = file_path.replace("\\", "/")
        name = Path(p).name
        return p.startswith("tests/") or "/tests/" in p or name.startswith("test_")

    def _impact_from_import_graph(self, modified_files: List[str]) -> Dict[str, Any]:
        """Infer impacted modules/tests from import dependencies."""
        self._build_import_graph()

        changed_modules: Set[str] = set()
        for file_path in modified_files:
            norm = file_path.replace("\\", "/")
            if not norm.endswith(".py"):
                continue
            mod = self.file_to_module.get(norm)
            if mod:
                changed_modules.add(mod)

        transitive = self._collect_transitive_dependents(changed_modules)
        impacted_modules = changed_modules | transitive

        pytest_targets: Set[str] = set()
        for mod in impacted_modules:
            file_path = self.module_to_file.get(mod)
            if file_path and self._is_test_file(file_path):
                pytest_targets.add(file_path)

        return {
            "changed_modules": changed_modules,
            "transitive_dependents": transitive,
            "impacted_modules": impacted_modules,
            "pytest_targets": pytest_targets,
        }

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
        impacted_modules: Set[str] = set()
        transitive_dependents: Set[str] = set()

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

        if self.config.impact_enable_import_graph:
            graph_impact = self._impact_from_import_graph(modified_files)
            impacted_modules.update(graph_impact["impacted_modules"])
            transitive_dependents.update(graph_impact["transitive_dependents"])
            pytest_targets.update(graph_impact["pytest_targets"])

        return {
            "modified_files": modified_files,
            "impacted_contexts": sorted(list(impacted_contexts)),
            "impacted_modules": sorted(list(impacted_modules)),
            "transitive_dependents": sorted(list(transitive_dependents)),
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
