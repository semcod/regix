# System Architecture Analysis
<!-- generated in 0.00s -->

## Overview

- **Project**: /home/tom/github/semcod/regix
- **Primary Language**: python
- **Languages**: python: 36, yaml: 4, json: 2, shell: 2, ini: 1
- **Analysis Mode**: static
- **Total Functions**: 221
- **Total Classes**: 44
- **Modules**: 48
- **Entry Points**: 158

## Architecture by Module

### regix.config
- **Functions**: 24
- **Classes**: 2
- **File**: `config.py`

### regix.smells
- **Functions**: 15
- **File**: `smells.py`

### regix.cli
- **Functions**: 15
- **File**: `cli.py`

### regix.benchmark.probes
- **Functions**: 14
- **Classes**: 6
- **File**: `probes.py`

### regix.impact
- **Functions**: 14
- **Classes**: 1
- **File**: `impact.py`

### regix.models
- **Functions**: 12
- **Classes**: 13
- **File**: `models.py`

### regix.backends.code2llm_backend
- **Functions**: 12
- **Classes**: 1
- **File**: `code2llm_backend.py`

### regix.snapshot
- **Functions**: 10
- **File**: `snapshot.py`

### regix.git
- **Functions**: 9
- **Classes**: 1
- **File**: `git.py`

### regix.benchmark.reporter
- **Functions**: 8
- **Classes**: 1
- **File**: `reporter.py`

### regix.backends.architecture_backend
- **Functions**: 7
- **Classes**: 1
- **File**: `architecture_backend.py`

### regix.backends.base
- **Functions**: 7
- **Classes**: 1
- **File**: `base.py`

### regix.backends.structure_backend
- **Functions**: 7
- **Classes**: 2
- **File**: `structure_backend.py`

### regix.compare
- **Functions**: 7
- **File**: `compare.py`

### regix
- **Functions**: 6
- **Classes**: 1
- **File**: `__init__.py`

### regix.benchmark.factory
- **Functions**: 6
- **File**: `factory.py`

### regix.cache
- **Functions**: 5
- **File**: `cache.py`

### regix.backends.coverage_backend
- **Functions**: 5
- **Classes**: 1
- **File**: `coverage_backend.py`

### regix.exceptions
- **Functions**: 4
- **Classes**: 5
- **File**: `exceptions.py`

### regix.history
- **Functions**: 4
- **File**: `history.py`

## Key Entry Points

Main execution flows into the system:

### regix.benchmark.factory.build_regix_suite
> Build the default regix benchmark suite.
- **Calls**: BenchmarkSuite, suite.add, suite.add, suite.add, suite.add, suite.add, suite.add, suite.add

### regix.cli.compare
> Compare metrics between two git refs or local state.
- **Calls**: app.command, typer.Argument, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### regix.benchmark.reporter.BenchmarkReporter.print_rich
- **Calls**: Console, console.print, console.print, suites.items, len, sum, sum, sum

### regix.impact.ImpactAnalyzer.analyze_impact
> Performs change-impact analysis and maps files to selective tests.
- **Calls**: set, set, set, set, self._map_scenarios, testql_scenarios.update, visual_diff_routes.update, Path

### regix.models.RegressionReport.to_toon
> TOON format — machine-readable plain text.
- **Calls**: None.strftime, lines.append, lines.append, lines.append, lines.append, lines.append, lines.extend, lines.extend

### regix.cli.status
> Show Regix configuration and available backends.
- **Calls**: app.command, typer.Option, typer.Option, regix.cli._load_config, typer.echo, typer.echo, typer.echo, typer.echo

### regix.cli.impact
> Analyze git changes and print or execute targeted selective test suites.
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, ImpactAnalyzer, analyzer.get_git_modified_files, typer.echo

### regix.benchmark.probes.BackendProbe.run
- **Calls**: regix.backends.base.get_backend, Path, regix.benchmark.probes._measurement_error, backend.is_available, BenchmarkResult, tempfile.mkdtemp, self._generate_files, RegressionConfig

### regix.cli.diff
> Show symbol-by-symbol metric diff (like git diff for metrics).
- **Calls**: app.command, typer.Argument, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, regix.cli._load_config

### regix.cli.gates
> Check current state against configured quality gates (absolute thresholds).
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, regix.cli._load_config, None.resolve, regix.snapshot.capture

### regix.integrations.RegixCollector._parse
- **Calls**: path.read_text, text.splitlines, json.loads, line.strip, line.startswith, line.startswith, line.startswith, data.get

### regix.cli.snapshot
> Capture and store a snapshot without comparing.
- **Calls**: app.command, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, regix.cli._load_config, None.resolve

### regix.compare.compare
> Compare two snapshots and produce a regression report.
- **Calls**: time.monotonic, sorted, regix.compare._count_severity_in_list, regix.compare._count_severity_in_list, regix.smells.detect_smells, regix.compare._count_severity_in_list, regix.compare._count_severity_in_list, RegressionReport

### regix.cli.history
> Show metric timeline across N historical commits.
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### regix.backends.vallm_backend.VallmBackend.collect
> Run ``vallm batch`` and collect quality scores per file.
- **Calls**: self.is_available, subprocess.run, json.loads, set, isinstance, data.get, entry.get, entry.get

### regix.impact.ImpactAnalyzer.get_git_modified_files
> Detects changed, added, and untracked files in git workspace.
- **Calls**: subprocess.run, subprocess.run, sorted, line.strip, any, filtered_files.append, list, str

### regix.backends.code2llm_backend.Code2llmBackend._parse_map_toon
> Parse map.toon.yaml and extract file-level and symbol metrics.
- **Calls**: self._parse_header_stats, content.splitlines, map_file.exists, map_file.read_text, line.startswith, line.startswith, self._parse_module_list_entry, line.endswith

### regix.backends.code2llm_backend.Code2llmBackend._parse_evolution_toon
> Parse evolution.toon.yaml for complexity alerts and hotspots.
- **Calls**: content.splitlines, evo_file.exists, evo_file.read_text, line.startswith, None.startswith, self._parse_next_action_line, self._parse_cc_from_line, line.strip

### scripts.check_regression.check_regression
> Main regression check function.
- **Calls**: scripts.check_regression.load_json_file, scripts.check_regression.load_json_file, scripts.check_regression.load_json_file, None.append, open, json.dump, regix.benchmark.reporter.BenchmarkReporter.print, sys.exit

### regix.backends.architecture_backend.ArchitectureBackend._symbol_metrics
- **Calls**: getattr, max, sum, round, SymbolMetrics, str, sum, ArchitectureBackend._param_count

### regix.backends.structure_backend.StructureBackend.collect
> Collect fan_out, call_count per function and symbol_count per file.
- **Calls**: str, self._collect_functions, results.append, ast.parse, SymbolMetrics, regix.backends.structure_backend._analyse_function, results.append, full.read_text

### regix.benchmark.reporter.BenchmarkReporter.print_plain
- **Calls**: suites.items, None.append, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print

### regix.impact.ImpactAnalyzer._load_swop_mappings
> Loads CQRS and SWOP mappings if present in the workspace.
- **Calls**: manifests_dir.glob, manifests_dir.exists, manifest_file.read_text, data.get, yaml.safe_load, self._fallback_yaml_parse, data.get, item.get

### regix.cache.lookup
> Return cached snapshot or None.
- **Calls**: regix.cache._cache_dir, regix.cache._cache_key, path.exists, None.decode, json.loads, Snapshot, SymbolMetrics, gzip.decompress

### regix.benchmark.cli.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.add_argument, parser.add_argument, parser.parse_args, importlib.import_module, benchmark_pkg.build_regix_suite

### regix.backends.docstring_backend.DocstringBackend.collect
> Compute docstring coverage per file.
- **Calls**: str, ast.walk, results.append, ast.parse, isinstance, SymbolMetrics, full.read_text, ast.get_docstring

### regix.backends.radon_backend.RadonBackend.collect
> Collect MI (module-level) and CC (per-function) using radon.
- **Calls**: str, results.append, mi_visit, cc_visit, SymbolMetrics, results.append, full.read_text, SymbolMetrics

### regix.benchmark.probes.ImportProbe.run
- **Calls**: range, BenchmarkResult, time.perf_counter, regix.benchmark.probes._measurement_error, subprocess.run, times.append, min, time.perf_counter

### regix.benchmark.probes.CLIProbe.run
- **Calls**: range, BenchmarkResult, time.perf_counter, regix.benchmark.probes._measurement_error, subprocess.run, times.append, min, time.perf_counter

### regix.benchmark.probes.UnitTestProbe.run
- **Calls**: time.perf_counter, output.splitlines, BenchmarkResult, str, subprocess.run, None.strip, time.perf_counter, regix.benchmark.probes._measurement_error

## Process Flows

Key execution flows identified:

### Flow 1: build_regix_suite
```
build_regix_suite [regix.benchmark.factory]
```

### Flow 2: compare
```
compare [regix.cli]
```

### Flow 3: print_rich
```
print_rich [regix.benchmark.reporter.BenchmarkReporter]
```

### Flow 4: analyze_impact
```
analyze_impact [regix.impact.ImpactAnalyzer]
```

### Flow 5: to_toon
```
to_toon [regix.models.RegressionReport]
```

### Flow 6: status
```
status [regix.cli]
  └─> _load_config
```

### Flow 7: impact
```
impact [regix.cli]
```

### Flow 8: run
```
run [regix.benchmark.probes.BackendProbe]
  └─ →> get_backend
  └─ →> _measurement_error
```

### Flow 9: diff
```
diff [regix.cli]
```

### Flow 10: gates
```
gates [regix.cli]
```

## Key Classes

### regix.config.RegressionConfig
> All user-configurable values for a Regix run.
- **Methods**: 35
- **Key Methods**: regix.config.RegressionConfig.cc_max, regix.config.RegressionConfig.cc_max, regix.config.RegressionConfig.mi_min, regix.config.RegressionConfig.mi_min, regix.config.RegressionConfig.coverage_min, regix.config.RegressionConfig.coverage_min, regix.config.RegressionConfig.length_max, regix.config.RegressionConfig.length_max, regix.config.RegressionConfig.docstring_min, regix.config.RegressionConfig.docstring_min

### regix.impact.ImpactAnalyzer
> Generic impact analyzer for local code changes and test suite mapping.
- **Methods**: 14
- **Key Methods**: regix.impact.ImpactAnalyzer.__init__, regix.impact.ImpactAnalyzer._load_swop_mappings, regix.impact.ImpactAnalyzer._parse_yaml_section_header, regix.impact.ImpactAnalyzer._parse_yaml_item_start, regix.impact.ImpactAnalyzer._parse_yaml_item_field, regix.impact.ImpactAnalyzer._fallback_yaml_parse, regix.impact.ImpactAnalyzer.get_git_modified_files, regix.impact.ImpactAnalyzer._map_folder_to_context, regix.impact.ImpactAnalyzer._map_swop_manifest, regix.impact.ImpactAnalyzer._map_python_unit_tests

### regix.models.RegressionReport
> Aggregated result of a comparison between two snapshots.
- **Methods**: 13
- **Key Methods**: regix.models.RegressionReport.has_errors, regix.models.RegressionReport.has_regressions, regix.models.RegressionReport.passed, regix.models.RegressionReport.summary, regix.models.RegressionReport.to_dict, regix.models.RegressionReport.to_json, regix.models.RegressionReport.to_yaml, regix.models.RegressionReport._toon_regression_section, regix.models.RegressionReport._toon_smell_section, regix.models.RegressionReport.to_toon

### regix.backends.code2llm_backend.Code2llmBackend
> Code2llm TOON YAML parser for rich structural metrics.

Generates metrics from code2llm output:
  - 
- **Methods**: 12
- **Key Methods**: regix.backends.code2llm_backend.Code2llmBackend.is_available, regix.backends.code2llm_backend.Code2llmBackend.version, regix.backends.code2llm_backend.Code2llmBackend._run_code2llm, regix.backends.code2llm_backend.Code2llmBackend._parse_header_stats, regix.backends.code2llm_backend.Code2llmBackend._parse_module_list_entry, regix.backends.code2llm_backend.Code2llmBackend._parse_function_entry, regix.backends.code2llm_backend.Code2llmBackend._parse_map_toon, regix.backends.code2llm_backend.Code2llmBackend._parse_next_action_line, regix.backends.code2llm_backend.Code2llmBackend._parse_cc_from_line, regix.backends.code2llm_backend.Code2llmBackend._parse_target_to_symbol_file
- **Inherits**: BackendBase

### regix.backends.architecture_backend.ArchitectureBackend
> Computes per-function structural metrics via AST for smell detection.
- **Methods**: 7
- **Key Methods**: regix.backends.architecture_backend.ArchitectureBackend.is_available, regix.backends.architecture_backend.ArchitectureBackend.version, regix.backends.architecture_backend.ArchitectureBackend._read_source, regix.backends.architecture_backend.ArchitectureBackend._iter_functions, regix.backends.architecture_backend.ArchitectureBackend._param_count, regix.backends.architecture_backend.ArchitectureBackend._symbol_metrics, regix.backends.architecture_backend.ArchitectureBackend.collect
- **Inherits**: BackendBase

### regix.benchmark.reporter.BenchmarkReporter
> Prints results as a rich table or plain text.
- **Methods**: 7
- **Key Methods**: regix.benchmark.reporter.BenchmarkReporter.__init__, regix.benchmark.reporter.BenchmarkReporter._format_result_details, regix.benchmark.reporter.BenchmarkReporter.print_rich, regix.benchmark.reporter.BenchmarkReporter.print_plain, regix.benchmark.reporter.BenchmarkReporter.print_json, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.any_failed

### regix.Regix
> Main entry point — wraps snapshot, compare, and history.
- **Methods**: 6
- **Key Methods**: regix.Regix.__init__, regix.Regix.snapshot, regix.Regix.compare, regix.Regix.compare_local, regix.Regix.history, regix.Regix.check_gates

### regix.backends.coverage_backend.CoverageBackend
- **Methods**: 5
- **Key Methods**: regix.backends.coverage_backend.CoverageBackend.is_available, regix.backends.coverage_backend.CoverageBackend.version, regix.backends.coverage_backend.CoverageBackend.collect, regix.backends.coverage_backend.CoverageBackend._from_json, regix.backends.coverage_backend.CoverageBackend._from_coverage_file
- **Inherits**: BackendBase

### regix.backends.base.BackendBase
> Interface that all analysis backends must implement.
- **Methods**: 4
- **Key Methods**: regix.backends.base.BackendBase.is_available, regix.backends.base.BackendBase.collect, regix.backends.base.BackendBase.version, regix.backends.base.BackendBase._python_version
- **Inherits**: ABC

### regix.backends.structure_backend.StructureBackend
> AST-based structural metrics: fan_out, call_count, symbol_count.
- **Methods**: 4
- **Key Methods**: regix.backends.structure_backend.StructureBackend.is_available, regix.backends.structure_backend.StructureBackend.version, regix.backends.structure_backend.StructureBackend.collect, regix.backends.structure_backend.StructureBackend._collect_functions
- **Inherits**: BackendBase

### regix.models.Snapshot
> Immutable record of all SymbolMetrics for a codebase at a point in time.
- **Methods**: 4
- **Key Methods**: regix.models.Snapshot.metrics, regix.models.Snapshot.get, regix.models.Snapshot.save, regix.models.Snapshot.load

### regix.backends.docstring_backend.DocstringBackend
> Measure docstring coverage using the ``ast`` module.
- **Methods**: 3
- **Key Methods**: regix.backends.docstring_backend.DocstringBackend.is_available, regix.backends.docstring_backend.DocstringBackend.version, regix.backends.docstring_backend.DocstringBackend.collect
- **Inherits**: BackendBase

### regix.backends.radon_backend.RadonBackend
> Maintainability index and cyclomatic complexity via ``radon``.
- **Methods**: 3
- **Key Methods**: regix.backends.radon_backend.RadonBackend.is_available, regix.backends.radon_backend.RadonBackend.version, regix.backends.radon_backend.RadonBackend.collect
- **Inherits**: BackendBase

### regix.backends.vallm_backend.VallmBackend
> LLM-based code quality scoring via the ``vallm`` CLI tool.
- **Methods**: 3
- **Key Methods**: regix.backends.vallm_backend.VallmBackend.is_available, regix.backends.vallm_backend.VallmBackend.version, regix.backends.vallm_backend.VallmBackend.collect
- **Inherits**: BackendBase

### regix.backends.lizard_backend.LizardBackend
> Cyclomatic complexity and function length via the ``lizard`` library.
- **Methods**: 3
- **Key Methods**: regix.backends.lizard_backend.LizardBackend.is_available, regix.backends.lizard_backend.LizardBackend.version, regix.backends.lizard_backend.LizardBackend.collect
- **Inherits**: BackendBase

### regix.benchmark.models.BenchmarkResult
- **Methods**: 3
- **Key Methods**: regix.benchmark.models.BenchmarkResult.passed, regix.benchmark.models.BenchmarkResult.status, regix.benchmark.models.BenchmarkResult.to_dict

### regix.benchmark.suite.BenchmarkSuite
> Collects probes and runs them.
- **Methods**: 3
- **Key Methods**: regix.benchmark.suite.BenchmarkSuite.__init__, regix.benchmark.suite.BenchmarkSuite.add, regix.benchmark.suite.BenchmarkSuite.run

### regix.benchmark.probes.UnitTestProbe
- **Methods**: 3
- **Key Methods**: regix.benchmark.probes.UnitTestProbe.__init__, regix.benchmark.probes.UnitTestProbe._pytest_env, regix.benchmark.probes.UnitTestProbe.run
- **Inherits**: BenchmarkProbe

### regix.benchmark.probes.BackendProbe
> Measures a regix backend's collect() throughput on synthetic files.
- **Methods**: 3
- **Key Methods**: regix.benchmark.probes.BackendProbe.__init__, regix.benchmark.probes.BackendProbe._generate_files, regix.benchmark.probes.BackendProbe.run
- **Inherits**: BenchmarkProbe

### regix.models.GateResult
> Aggregate gate evaluation result.
- **Methods**: 3
- **Key Methods**: regix.models.GateResult.all_passed, regix.models.GateResult.errors, regix.models.GateResult.warnings

## Data Transformation Functions

Key functions that process and transform data:

### regix.config.RegressionConfig._parse_gates
> Parse gates.hard / gates.target (new format).
- **Output to**: root.get, int, isinstance, GateThresholds, float

### regix.config.RegressionConfig._parse_legacy_metrics
> Parse legacy flat metrics: cc_max, mi_min, cc_target, …
- **Output to**: root.get, _MAP.items, float, GateThresholds, mapping.items

### regix.config.RegressionConfig._parse_deltas
> Parse deltas (new) and thresholds (legacy).
- **Output to**: root.get, root.get, float, float, kwargs.setdefault

### regix.config.RegressionConfig._parse_smells
> Parse architectural smell thresholds.
- **Output to**: root.get, int, float

### regix.config.RegressionConfig._parse_files
> Parse include/exclude patterns.

### regix.config.RegressionConfig._parse_backends
> Parse backend configuration.
- **Output to**: isinstance, bk.items

### regix.config.RegressionConfig._parse_output
> Parse output format settings.
- **Output to**: root.get, _KEYS.items

### regix.config.RegressionConfig._parse_cache
> Parse cache settings.
- **Output to**: root.get

### regix.config.RegressionConfig._parse_loop
> Parse loop settings.
- **Output to**: root.get, int

### regix.benchmark.reporter.BenchmarkReporter._format_result_details
> Build the details string for a single benchmark result.
- **Output to**: None.join, parts.append, parts.append

### regix.benchmark.factory._make_config_parse_probe
> Benchmark config parsing throughput.
- **Output to**: ThroughputProbe, tempfile.mkdtemp, cfg_path.write_text, str, RegressionConfig.from_file

### regix.integrations.RegixCollector._parse
- **Output to**: path.read_text, text.splitlines, json.loads, line.strip, line.startswith

### regix.impact.ImpactAnalyzer._parse_yaml_section_header
> Parse YAML section header. Returns section name or None.
- **Output to**: line.startswith, line.startswith, line.startswith

### regix.impact.ImpactAnalyzer._parse_yaml_item_start
> Parse start of a YAML item. Returns new item dict or None.
- **Output to**: re.search, name_match.group

### regix.impact.ImpactAnalyzer._parse_yaml_item_field
> Parse a YAML item field and update item dict.
- **Output to**: re.search, file_match.group, re.search, class_match.group

### regix.impact.ImpactAnalyzer._fallback_yaml_parse
> Simple fallback YAML parser to avoid external dependencies in regix core.
- **Output to**: re.search, content.splitlines, context_match.group, self._parse_yaml_section_header, None.append

### regix.compare._process_comparison_key
> Process one (file, symbol) key.

Returns (regressions, improvements, changed, skip).
- **Output to**: idx_before.get, idx_after.get, regix.compare._compare_symbol_metrics, regix.compare._collect_deleted_symbol

### regix.backends.code2llm_backend.Code2llmBackend._parse_header_stats
> Parse header stats from toon content.
- **Output to**: content.splitlines, _HEADER_STATS_RE.match, int, float, match.group

### regix.backends.code2llm_backend.Code2llmBackend._parse_module_list_entry
> Parse a module list entry line. Returns (file, line_count) or (None, None).
- **Output to**: None.split, None.isdigit, line.strip, len, int

### regix.backends.code2llm_backend.Code2llmBackend._parse_function_entry
> Parse a function entry line. Returns SymbolMetrics or None.
- **Output to**: line.strip, _FUNCTION_RE.match, match.group, match.group, SymbolMetrics

### regix.backends.code2llm_backend.Code2llmBackend._parse_map_toon
> Parse map.toon.yaml and extract file-level and symbol metrics.
- **Output to**: self._parse_header_stats, content.splitlines, map_file.exists, map_file.read_text, line.startswith

### regix.backends.code2llm_backend.Code2llmBackend._parse_next_action_line
> Parse a NEXT action line. Returns (action, target) or (None, None).
- **Output to**: re.search, match.groups

### regix.backends.code2llm_backend.Code2llmBackend._parse_cc_from_line
> Extract CC value from a line. Returns CC or None.
- **Output to**: re.search, int, cc_match.group

### regix.backends.code2llm_backend.Code2llmBackend._parse_target_to_symbol_file
> Parse target string into (symbol, file_path). Returns (None, None) if invalid.
- **Output to**: target.split, len

### regix.backends.code2llm_backend.Code2llmBackend._parse_evolution_toon
> Parse evolution.toon.yaml for complexity alerts and hotspots.
- **Output to**: content.splitlines, evo_file.exists, evo_file.read_text, line.startswith, None.startswith

## Behavioral Patterns

### recursion_check_gates
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: regix.Regix.check_gates

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `regix.benchmark.factory.build_regix_suite` - 43 calls
- `regix.cli.compare` - 29 calls
- `regix.benchmark.reporter.BenchmarkReporter.print_rich` - 27 calls
- `regix.impact.ImpactAnalyzer.analyze_impact` - 26 calls
- `regix.models.RegressionReport.to_toon` - 24 calls
- `regix.cli.status` - 23 calls
- `regix.cli.impact` - 23 calls
- `regix.benchmark.probes.BackendProbe.run` - 21 calls
- `regix.integrations.planfile.sync_regressions_to_planfile` - 21 calls
- `regix.cli.diff` - 21 calls
- `regix.cli.gates` - 21 calls
- `regix.cli.snapshot` - 17 calls
- `regix.compare.compare` - 17 calls
- `regix.report.render_history` - 16 calls
- `regix.cli.history` - 16 calls
- `regix.backends.vallm_backend.VallmBackend.collect` - 15 calls
- `regix.impact.ImpactAnalyzer.get_git_modified_files` - 15 calls
- `scripts.check_regression.check_regression` - 14 calls
- `regix.backends.structure_backend.StructureBackend.collect` - 14 calls
- `regix.benchmark.reporter.BenchmarkReporter.print_plain` - 14 calls
- `regix.cache.lookup` - 13 calls
- `regix.benchmark.cli.main` - 13 calls
- `regix.git.read_tree_sources` - 12 calls
- `regix.backends.docstring_backend.DocstringBackend.collect` - 12 calls
- `regix.backends.radon_backend.RadonBackend.collect` - 12 calls
- `regix.benchmark.probes.ImportProbe.run` - 12 calls
- `regix.benchmark.probes.CLIProbe.run` - 12 calls
- `regix.benchmark.probes.UnitTestProbe.run` - 12 calls
- `regix.benchmark.probes.ThroughputProbe.run` - 12 calls
- `regix.impact.ImpactAnalyzer.execute_targeted_tests` - 12 calls
- `regix.snapshot.capture` - 12 calls
- `regix.config.RegressionConfig.from_dict` - 11 calls
- `regix.gates.check_gates` - 10 calls
- `regix.git.checkout_temporary` - 10 calls
- `regix.report.render` - 10 calls
- `regix.models.Snapshot.load` - 10 calls
- `regix.cache.store` - 9 calls
- `regix.backends.architecture_backend.ArchitectureBackend.collect` - 9 calls
- `regix.backends.lizard_backend.LizardBackend.collect` - 9 calls
- `regix.cli.init` - 9 calls

## System Interactions

How components interact:

```mermaid
graph TD
    build_regix_suite --> BenchmarkSuite
    build_regix_suite --> add
    compare --> command
    compare --> Argument
    compare --> Option
    print_rich --> Console
    print_rich --> print
    print_rich --> items
    print_rich --> len
    analyze_impact --> set
    analyze_impact --> _map_scenarios
    to_toon --> strftime
    to_toon --> append
    status --> command
    status --> Option
    status --> _load_config
    status --> echo
    impact --> command
    impact --> Option
    run --> get_backend
    run --> Path
    run --> _measurement_error
    run --> is_available
    run --> BenchmarkResult
    diff --> command
    diff --> Argument
    diff --> Option
    gates --> command
    gates --> Option
    _parse --> read_text
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.