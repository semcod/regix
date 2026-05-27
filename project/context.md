# System Architecture Analysis
<!-- generated in 0.00s -->

## Overview

- **Project**: /home/tom/github/semcod/regix
- **Primary Language**: python
- **Languages**: python: 36, yaml: 4, json: 2, shell: 2, ini: 1
- **Analysis Mode**: static
- **Total Functions**: 196
- **Total Classes**: 44
- **Modules**: 48
- **Entry Points**: 143

## Architecture by Module

### regix.config
- **Functions**: 24
- **Classes**: 2
- **File**: `config.py`

### regix.smells
- **Functions**: 15
- **File**: `smells.py`

### regix.benchmark.probes
- **Functions**: 14
- **Classes**: 6
- **File**: `probes.py`

### regix.models
- **Functions**: 11
- **Classes**: 13
- **File**: `models.py`

### regix.cli
- **Functions**: 9
- **File**: `cli.py`

### regix.git
- **Functions**: 9
- **Classes**: 1
- **File**: `git.py`

### regix.benchmark.reporter
- **Functions**: 8
- **Classes**: 1
- **File**: `reporter.py`

### regix.backends.base
- **Functions**: 7
- **Classes**: 1
- **File**: `base.py`

### regix.backends.architecture_backend
- **Functions**: 7
- **Classes**: 1
- **File**: `architecture_backend.py`

### regix.snapshot
- **Functions**: 7
- **File**: `snapshot.py`

### regix.backends.structure_backend
- **Functions**: 7
- **Classes**: 2
- **File**: `structure_backend.py`

### regix
- **Functions**: 6
- **Classes**: 1
- **File**: `__init__.py`

### regix.backends.code2llm_backend
- **Functions**: 6
- **Classes**: 1
- **File**: `code2llm_backend.py`

### regix.impact
- **Functions**: 6
- **Classes**: 1
- **File**: `impact.py`

### regix.compare
- **Functions**: 6
- **File**: `compare.py`

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

### regix.cli.impact
> Analyze git changes and print or execute targeted selective test suites.
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, ImpactAnalyzer, analyzer.get_git_modified_files, typer.echo

### regix.impact.ImpactAnalyzer.analyze_impact
> Performs change-impact analysis and maps files to selective tests.
- **Calls**: set, set, set, set, scenarios_dir.exists, Path, str, self.dependency_graph.items

### regix.backends.code2llm_backend.Code2llmBackend._parse_map_toon
> Parse map.toon.yaml and extract file-level and symbol metrics.
- **Calls**: content.splitlines, enumerate, map_file.exists, map_file.read_text, content.splitlines, _HEADER_STATS_RE.match, line.startswith, int

### regix.cli.compare
> Compare metrics between two git refs or local state.
- **Calls**: app.command, typer.Argument, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### regix.benchmark.reporter.BenchmarkReporter.print_rich
- **Calls**: Console, console.print, console.print, suites.items, len, sum, sum, sum

### regix.models.RegressionReport.to_toon
> TOON format — machine-readable plain text.
- **Calls**: None.strftime, lines.append, lines.append, lines.append, lines.append, lines.append, lines.extend, lines.extend

### regix.cli.status
> Show Regix configuration and available backends.
- **Calls**: app.command, typer.Option, typer.Option, regix.cli._load_config, typer.echo, typer.echo, typer.echo, typer.echo

### regix.cli.diff
> Show symbol-by-symbol metric diff (like git diff for metrics).
- **Calls**: app.command, typer.Argument, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, regix.cli._load_config

### regix.cli.gates
> Check current state against configured quality gates (absolute thresholds).
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, regix.cli._load_config, None.resolve, regix.snapshot.capture

### regix.benchmark.probes.BackendProbe.run
- **Calls**: regix.backends.base.get_backend, Path, regix.benchmark.probes._measurement_error, backend.is_available, BenchmarkResult, tempfile.mkdtemp, self._generate_files, RegressionConfig

### regix.backends.code2llm_backend.Code2llmBackend._parse_evolution_toon
> Parse evolution.toon.yaml for complexity alerts and hotspots.
- **Calls**: content.splitlines, evo_file.exists, evo_file.read_text, line.startswith, None.startswith, re.search, re.search, line.strip

### regix.integrations.RegixCollector._parse
- **Calls**: path.read_text, text.splitlines, json.loads, line.strip, line.startswith, line.startswith, line.startswith, data.get

### regix.compare.compare
> Compare two snapshots and produce a regression report.
- **Calls**: time.monotonic, sorted, sum, sum, regix.smells.detect_smells, sum, sum, RegressionReport

### regix.cli.snapshot
> Capture and store a snapshot without comparing.
- **Calls**: app.command, typer.Argument, typer.Option, typer.Option, typer.Option, typer.Option, regix.cli._load_config, None.resolve

### regix.impact.ImpactAnalyzer._fallback_yaml_parse
> Simple fallback YAML parser to avoid external dependencies in regix core.
- **Calls**: re.search, content.splitlines, context_match.group, line.startswith, None.append, line.startswith, line.startswith, None.startswith

### regix.cli.history
> Show metric timeline across N historical commits.
- **Calls**: app.command, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option, typer.Option

### regix.backends.vallm_backend.VallmBackend.collect
> Run ``vallm batch`` and collect quality scores per file.
- **Calls**: self.is_available, subprocess.run, json.loads, set, isinstance, data.get, entry.get, entry.get

### regix.impact.ImpactAnalyzer.get_git_modified_files
> Detects changed, added, and untracked files in git workspace.
- **Calls**: subprocess.run, subprocess.run, sorted, line.strip, any, filtered_files.append, list, str

### regix.backends.architecture_backend.ArchitectureBackend._symbol_metrics
- **Calls**: getattr, max, sum, round, SymbolMetrics, str, sum, ArchitectureBackend._param_count

### regix.benchmark.reporter.BenchmarkReporter.print_plain
- **Calls**: suites.items, None.append, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.print

### scripts.check_regression.check_regression
> Main regression check function.
- **Calls**: scripts.check_regression.load_json_file, scripts.check_regression.load_json_file, scripts.check_regression.load_json_file, None.append, open, json.dump, regix.benchmark.reporter.BenchmarkReporter.print, sys.exit

### regix.impact.ImpactAnalyzer._load_swop_mappings
> Loads CQRS and SWOP mappings if present in the workspace.
- **Calls**: manifests_dir.glob, manifests_dir.exists, manifest_file.read_text, data.get, yaml.safe_load, self._fallback_yaml_parse, data.get, item.get

### regix.backends.structure_backend.StructureBackend.collect
> Collect fan_out, call_count per function and symbol_count per file.
- **Calls**: str, self._collect_functions, results.append, ast.parse, SymbolMetrics, regix.backends.structure_backend._analyse_function, results.append, full.read_text

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

### regix.impact.ImpactAnalyzer.execute_targeted_tests
> Runs the matched targeted test suites selectively.
- **Calls**: None.append, subprocess.run, None.append, None.append, subprocess.run, None.append, None.join, str

### regix.benchmark.probes.ImportProbe.run
- **Calls**: range, BenchmarkResult, time.perf_counter, regix.benchmark.probes._measurement_error, subprocess.run, times.append, min, time.perf_counter

## Process Flows

Key execution flows identified:

### Flow 1: build_regix_suite
```
build_regix_suite [regix.benchmark.factory]
```

### Flow 2: impact
```
impact [regix.cli]
```

### Flow 3: analyze_impact
```
analyze_impact [regix.impact.ImpactAnalyzer]
```

### Flow 4: _parse_map_toon
```
_parse_map_toon [regix.backends.code2llm_backend.Code2llmBackend]
```

### Flow 5: compare
```
compare [regix.cli]
```

### Flow 6: print_rich
```
print_rich [regix.benchmark.reporter.BenchmarkReporter]
```

### Flow 7: to_toon
```
to_toon [regix.models.RegressionReport]
```

### Flow 8: status
```
status [regix.cli]
  └─> _load_config
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

### regix.models.RegressionReport
> Aggregated result of a comparison between two snapshots.
- **Methods**: 12
- **Key Methods**: regix.models.RegressionReport.has_errors, regix.models.RegressionReport.has_regressions, regix.models.RegressionReport.passed, regix.models.RegressionReport.summary, regix.models.RegressionReport.to_dict, regix.models.RegressionReport.to_json, regix.models.RegressionReport.to_yaml, regix.models.RegressionReport._toon_regression_section, regix.models.RegressionReport._toon_smell_section, regix.models.RegressionReport.to_toon

### regix.backends.architecture_backend.ArchitectureBackend
> Computes per-function structural metrics via AST for smell detection.
- **Methods**: 7
- **Key Methods**: regix.backends.architecture_backend.ArchitectureBackend.is_available, regix.backends.architecture_backend.ArchitectureBackend.version, regix.backends.architecture_backend.ArchitectureBackend._read_source, regix.backends.architecture_backend.ArchitectureBackend._iter_functions, regix.backends.architecture_backend.ArchitectureBackend._param_count, regix.backends.architecture_backend.ArchitectureBackend._symbol_metrics, regix.backends.architecture_backend.ArchitectureBackend.collect
- **Inherits**: BackendBase

### regix.benchmark.reporter.BenchmarkReporter
> Prints results as a rich table or plain text.
- **Methods**: 7
- **Key Methods**: regix.benchmark.reporter.BenchmarkReporter.__init__, regix.benchmark.reporter.BenchmarkReporter._format_result_details, regix.benchmark.reporter.BenchmarkReporter.print_rich, regix.benchmark.reporter.BenchmarkReporter.print_plain, regix.benchmark.reporter.BenchmarkReporter.print_json, regix.benchmark.reporter.BenchmarkReporter.print, regix.benchmark.reporter.BenchmarkReporter.any_failed

### regix.backends.code2llm_backend.Code2llmBackend
> Code2llm TOON YAML parser for rich structural metrics.

Generates metrics from code2llm output:
  - 
- **Methods**: 6
- **Key Methods**: regix.backends.code2llm_backend.Code2llmBackend.is_available, regix.backends.code2llm_backend.Code2llmBackend.version, regix.backends.code2llm_backend.Code2llmBackend._run_code2llm, regix.backends.code2llm_backend.Code2llmBackend._parse_map_toon, regix.backends.code2llm_backend.Code2llmBackend._parse_evolution_toon, regix.backends.code2llm_backend.Code2llmBackend.collect
- **Inherits**: BackendBase

### regix.impact.ImpactAnalyzer
> Generic impact analyzer for local code changes and test suite mapping.
- **Methods**: 6
- **Key Methods**: regix.impact.ImpactAnalyzer.__init__, regix.impact.ImpactAnalyzer._load_swop_mappings, regix.impact.ImpactAnalyzer._fallback_yaml_parse, regix.impact.ImpactAnalyzer.get_git_modified_files, regix.impact.ImpactAnalyzer.analyze_impact, regix.impact.ImpactAnalyzer.execute_targeted_tests

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

### regix.models.Snapshot
> Immutable record of all SymbolMetrics for a codebase at a point in time.
- **Methods**: 4
- **Key Methods**: regix.models.Snapshot.metrics, regix.models.Snapshot.get, regix.models.Snapshot.save, regix.models.Snapshot.load

### regix.backends.structure_backend.StructureBackend
> AST-based structural metrics: fan_out, call_count, symbol_count.
- **Methods**: 4
- **Key Methods**: regix.backends.structure_backend.StructureBackend.is_available, regix.backends.structure_backend.StructureBackend.version, regix.backends.structure_backend.StructureBackend.collect, regix.backends.structure_backend.StructureBackend._collect_functions
- **Inherits**: BackendBase

### regix.backends.docstring_backend.DocstringBackend
> Measure docstring coverage using the ``ast`` module.
- **Methods**: 3
- **Key Methods**: regix.backends.docstring_backend.DocstringBackend.is_available, regix.backends.docstring_backend.DocstringBackend.version, regix.backends.docstring_backend.DocstringBackend.collect
- **Inherits**: BackendBase

### regix.backends.vallm_backend.VallmBackend
> LLM-based code quality scoring via the ``vallm`` CLI tool.
- **Methods**: 3
- **Key Methods**: regix.backends.vallm_backend.VallmBackend.is_available, regix.backends.vallm_backend.VallmBackend.version, regix.backends.vallm_backend.VallmBackend.collect
- **Inherits**: BackendBase

### regix.backends.radon_backend.RadonBackend
> Maintainability index and cyclomatic complexity via ``radon``.
- **Methods**: 3
- **Key Methods**: regix.backends.radon_backend.RadonBackend.is_available, regix.backends.radon_backend.RadonBackend.version, regix.backends.radon_backend.RadonBackend.collect
- **Inherits**: BackendBase

### regix.backends.lizard_backend.LizardBackend
> Cyclomatic complexity and function length via the ``lizard`` library.
- **Methods**: 3
- **Key Methods**: regix.backends.lizard_backend.LizardBackend.is_available, regix.backends.lizard_backend.LizardBackend.version, regix.backends.lizard_backend.LizardBackend.collect
- **Inherits**: BackendBase

### regix.benchmark.suite.BenchmarkSuite
> Collects probes and runs them.
- **Methods**: 3
- **Key Methods**: regix.benchmark.suite.BenchmarkSuite.__init__, regix.benchmark.suite.BenchmarkSuite.add, regix.benchmark.suite.BenchmarkSuite.run

### regix.models.GateResult
> Aggregate gate evaluation result.
- **Methods**: 3
- **Key Methods**: regix.models.GateResult.all_passed, regix.models.GateResult.errors, regix.models.GateResult.warnings

### regix.benchmark.probes.UnitTestProbe
- **Methods**: 3
- **Key Methods**: regix.benchmark.probes.UnitTestProbe.__init__, regix.benchmark.probes.UnitTestProbe._pytest_env, regix.benchmark.probes.UnitTestProbe.run
- **Inherits**: BenchmarkProbe

### regix.benchmark.probes.BackendProbe
> Measures a regix backend's collect() throughput on synthetic files.
- **Methods**: 3
- **Key Methods**: regix.benchmark.probes.BackendProbe.__init__, regix.benchmark.probes.BackendProbe._generate_files, regix.benchmark.probes.BackendProbe.run
- **Inherits**: BenchmarkProbe

### regix.benchmark.models.BenchmarkResult
- **Methods**: 3
- **Key Methods**: regix.benchmark.models.BenchmarkResult.passed, regix.benchmark.models.BenchmarkResult.status, regix.benchmark.models.BenchmarkResult.to_dict

## Data Transformation Functions

Key functions that process and transform data:

### regix.backends.code2llm_backend.Code2llmBackend._parse_map_toon
> Parse map.toon.yaml and extract file-level and symbol metrics.
- **Output to**: content.splitlines, enumerate, map_file.exists, map_file.read_text, content.splitlines

### regix.backends.code2llm_backend.Code2llmBackend._parse_evolution_toon
> Parse evolution.toon.yaml for complexity alerts and hotspots.
- **Output to**: content.splitlines, evo_file.exists, evo_file.read_text, line.startswith, None.startswith

### regix.benchmark.reporter.BenchmarkReporter._format_result_details
> Build the details string for a single benchmark result.
- **Output to**: None.join, parts.append, parts.append

### regix.impact.ImpactAnalyzer._fallback_yaml_parse
> Simple fallback YAML parser to avoid external dependencies in regix core.
- **Output to**: re.search, content.splitlines, context_match.group, line.startswith, None.append

### regix.integrations.RegixCollector._parse
- **Output to**: path.read_text, text.splitlines, json.loads, line.strip, line.startswith

### regix.compare._process_comparison_key
> Process one (file, symbol) key.

Returns (regressions, improvements, changed, skip).
- **Output to**: idx_before.get, idx_after.get, regix.compare._compare_symbol_metrics, regix.compare._collect_deleted_symbol

### regix.benchmark.factory._make_config_parse_probe
> Benchmark config parsing throughput.
- **Output to**: ThroughputProbe, tempfile.mkdtemp, cfg_path.write_text, str, RegressionConfig.from_file

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

## Behavioral Patterns

### recursion_check_gates
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: regix.Regix.check_gates

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `regix.benchmark.factory.build_regix_suite` - 43 calls
- `regix.cli.impact` - 37 calls
- `regix.impact.ImpactAnalyzer.analyze_impact` - 32 calls
- `regix.cli.compare` - 29 calls
- `regix.benchmark.reporter.BenchmarkReporter.print_rich` - 27 calls
- `regix.models.RegressionReport.to_toon` - 24 calls
- `regix.cli.status` - 23 calls
- `regix.integrations.planfile.sync_regressions_to_planfile` - 21 calls
- `regix.cli.diff` - 21 calls
- `regix.cli.gates` - 21 calls
- `regix.benchmark.probes.BackendProbe.run` - 21 calls
- `regix.compare.compare` - 17 calls
- `regix.cli.snapshot` - 17 calls
- `regix.report.render_history` - 16 calls
- `regix.cli.history` - 16 calls
- `regix.backends.vallm_backend.VallmBackend.collect` - 15 calls
- `regix.impact.ImpactAnalyzer.get_git_modified_files` - 15 calls
- `regix.benchmark.reporter.BenchmarkReporter.print_plain` - 14 calls
- `scripts.check_regression.check_regression` - 14 calls
- `regix.backends.structure_backend.StructureBackend.collect` - 14 calls
- `regix.cache.lookup` - 13 calls
- `regix.benchmark.cli.main` - 13 calls
- `regix.backends.docstring_backend.DocstringBackend.collect` - 12 calls
- `regix.backends.radon_backend.RadonBackend.collect` - 12 calls
- `regix.impact.ImpactAnalyzer.execute_targeted_tests` - 12 calls
- `regix.snapshot.capture` - 12 calls
- `regix.benchmark.probes.ImportProbe.run` - 12 calls
- `regix.benchmark.probes.CLIProbe.run` - 12 calls
- `regix.benchmark.probes.UnitTestProbe.run` - 12 calls
- `regix.benchmark.probes.ThroughputProbe.run` - 12 calls
- `regix.git.read_tree_sources` - 12 calls
- `regix.config.RegressionConfig.from_dict` - 11 calls
- `regix.report.render` - 10 calls
- `regix.models.Snapshot.load` - 10 calls
- `regix.gates.check_gates` - 10 calls
- `regix.git.checkout_temporary` - 10 calls
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
    impact --> command
    impact --> Option
    analyze_impact --> set
    analyze_impact --> exists
    _parse_map_toon --> splitlines
    _parse_map_toon --> enumerate
    _parse_map_toon --> exists
    _parse_map_toon --> read_text
    compare --> command
    compare --> Argument
    compare --> Option
    print_rich --> Console
    print_rich --> print
    print_rich --> items
    print_rich --> len
    to_toon --> strftime
    to_toon --> append
    status --> command
    status --> Option
    status --> _load_config
    status --> echo
    diff --> command
    diff --> Argument
    diff --> Option
    gates --> command
    gates --> Option
    run --> get_backend
    run --> Path
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.