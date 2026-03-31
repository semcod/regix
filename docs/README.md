<!-- code2docs:start --># regix

![version](https://img.shields.io/badge/version-0.1.0-blue) ![python](https://img.shields.io/badge/python-%3E%3D3.9-blue) ![coverage](https://img.shields.io/badge/coverage-unknown-lightgrey) ![functions](https://img.shields.io/badge/functions-103-green)
> **103** functions | **31** classes | **24** files | CC̄ = 5.4

> Auto-generated project documentation from source code analysis.

**Author:** Tom Sapletta  
**License:** Apache-2.0[(LICENSE)](./LICENSE)  
**Repository:** [https://github.com/semcod/regix](https://github.com/semcod/regix)

## Installation

### From PyPI

```bash
pip install regix
```

### From Source

```bash
git clone https://github.com/semcod/regix
cd regix
pip install -e .
```

### Optional Extras

```bash
pip install regix[lizard]    # lizard features
pip install regix[radon]    # radon features
pip install regix[coverage]    # coverage features
pip install regix[vallm]    # vallm features
pip install regix[docstring]    # docstring features
pip install regix[full]    # full features
pip install regix[pyqual]    # pyqual features
pip install regix[dev]    # development tools
```

## Quick Start

### CLI Usage

```bash
# Generate full documentation for your project
regix ./my-project

# Only regenerate README
regix ./my-project --readme-only

# Preview what would be generated (no file writes)
regix ./my-project --dry-run

# Check documentation health
regix check ./my-project

# Sync — regenerate only changed modules
regix sync ./my-project
```

### Python API

```python
from regix import generate_readme, generate_docs, Code2DocsConfig

# Quick: generate README
generate_readme("./my-project")

# Full: generate all documentation
config = Code2DocsConfig(project_name="mylib", verbose=True)
docs = generate_docs("./my-project", config=config)
```

## Generated Output

When you run `regix`, the following files are produced:

```
<project>/
├── README.md                 # Main project README (auto-generated sections)
├── docs/
│   ├── api.md               # Consolidated API reference
│   ├── modules.md           # Module documentation with metrics
│   ├── architecture.md      # Architecture overview with diagrams
│   ├── dependency-graph.md  # Module dependency graphs
│   ├── coverage.md          # Docstring coverage report
│   ├── getting-started.md   # Getting started guide
│   ├── configuration.md    # Configuration reference
│   └── api-changelog.md    # API change tracking
├── examples/
│   ├── quickstart.py       # Basic usage examples
│   └── advanced_usage.py   # Advanced usage examples
├── CONTRIBUTING.md         # Contribution guidelines
└── mkdocs.yml             # MkDocs site configuration
```

## Configuration

Create `regix.yaml` in your project root (or run `regix init`):

```yaml
project:
  name: my-project
  source: ./
  output: ./docs/

readme:
  sections:
    - overview
    - install
    - quickstart
    - api
    - structure
  badges:
    - version
    - python
    - coverage
  sync_markers: true

docs:
  api_reference: true
  module_docs: true
  architecture: true
  changelog: true

examples:
  auto_generate: true
  from_entry_points: true

sync:
  strategy: markers    # markers | full | git-diff
  watch: false
  ignore:
    - "tests/"
    - "__pycache__"
```

## Sync Markers

regix can update only specific sections of an existing README using HTML comment markers:

```markdown
<!-- regix:start -->
# Project Title
... auto-generated content ...
<!-- regix:end -->
```

Content outside the markers is preserved when regenerating. Enable this with `sync_markers: true` in your configuration.

## Architecture

```
regix/
├── project    ├── exceptions    ├── gates    ├── check_regression    ├── compare    ├── git    ├── history    ├── config    ├── cli    ├── snapshot├── regix/    ├── cache    ├── report        ├── architecture_backend        ├── docstring_backend        ├── radon_backend    ├── backends/        ├── vallm_backend    ├── smells        ├── coverage_backend        ├── lizard_backend    ├── integrations/    ├── models        ├── structure_backend```

## API Overview

### Classes

- **`RegixError`** — Base exception for all Regix errors.
- **`GitRefError`** — Raised when a git ref cannot be resolved.
- **`GitDirtyError`** — Raised when the working tree is dirty and the operation requires a clean state.
- **`BackendError`** — Raised when a backend fails to produce output.
- **`ConfigError`** — Raised when the configuration file is invalid.
- **`CommitInfo`** — Lightweight commit metadata.
- **`RegressionConfig`** — All user-configurable values for a Regix run.
- **`Regix`** — Main entry point — wraps snapshot, compare, and history.
- **`ArchitectureBackend`** — Computes per-function structural metrics via AST for smell detection.
- **`DocstringBackend`** — —
- **`RadonBackend`** — —
- **`BackendBase`** — Interface that all analysis backends must implement.
- **`VallmBackend`** — —
- **`CoverageBackend`** — —
- **`LizardBackend`** — —
- **`RegixCollector`** — GateSet-compatible metric collector for pyqual.
- **`SymbolMetrics`** — All tracked metrics for a single symbol (function, class, or module).
- **`MetricDelta`** — Change in a single metric between two snapshots.
- **`ArchSmell`** — An architectural regression smell detected by cross-symbol analysis.
- **`Regression`** — A detected worsening of a metric between two snapshots.
- **`Improvement`** — A detected improvement of a metric between two snapshots.
- **`Snapshot`** — Immutable record of all SymbolMetrics for a codebase at a point in time.
- **`RegressionReport`** — Aggregated result of a comparison between two snapshots.
- **`CommitMetrics`** — Aggregated metrics for a single commit.
- **`HistoryRegression`** — A regression spanning multiple commits.
- **`TrendLine`** — Linear trend across commit history for a single metric.
- **`HistoryReport`** — Multi-commit metric timeline.
- **`GateCheck`** — Single gate threshold check.
- **`GateResult`** — Aggregate gate evaluation result.
- **`StructureBackend`** — —

### Functions

- `check_gates(snapshot, config)` — Evaluate absolute quality gates against a single snapshot.
- `run_command(cmd)` — Run a command and return its output
- `load_json_file(filepath)` — Load JSON file if it exists
- `check_regression()` — Main regression check function
- `compare(snap_before, snap_after, config)` — Compare two snapshots and produce a regression report.
- `resolve_ref(ref, workdir)` — Resolve a symbolic ref to a commit SHA.
- `list_commits(ref, depth, workdir)` — Return commit history starting from *ref*, newest first.
- `is_clean(workdir)` — Return True if there are no uncommitted changes.
- `get_dirty_files(workdir)` — Return files with uncommitted changes (modified + untracked).
- `get_changed_files(ref_a, ref_b, workdir)` — Return list of files changed between two refs.
- `checkout_temporary(ref, workdir)` — Context manager: create a git worktree at *ref* in a temp directory.
- `build_history(depth, ref, workdir, config)` — Walk ``depth`` commits and return a HistoryReport with metric timeline.
- `compare(ref_a, ref_b, local, config)` — Compare metrics between two git refs or local state.
- `history(depth, ref, metric, fmt)` — Show metric timeline across N historical commits.
- `snapshot(ref, fmt, output, config)` — Capture and store a snapshot without comparing.
- `diff(ref_a, ref_b, threshold, metric)` — Show symbol-by-symbol metric diff (like git diff for metrics).
- `gates(ref, fail_on, config, workdir)` — Check current state against configured quality gates (absolute thresholds).
- `status(config, workdir)` — Show Regix configuration and available backends.
- `init(workdir)` — Create a default regix.yaml in the project root.
- `capture(ref, workdir, config, backend_names)` — Capture a snapshot at a git ref or the local working tree.
- `lookup(commit_sha, backend_versions, cache_dir)` — Return cached snapshot or None.
- `store(snapshot, cache_dir)` — Store a snapshot in the cache, return its path.
- `clear(cache_dir)` — Remove all cached snapshots. Returns count removed.
- `render(report, fmt, output)` — Render a regression report in the specified format.
- `render_history(report, fmt)` — Render a history report.
- `register_backend(backend)` — Register a backend instance for use by Regix.
- `get_backend(name)` — Look up a registered backend by name.
- `available_backends()` — Return names of all registered backends.
- `detect_smells(snap_before, snap_after, config)` — Compare two snapshots and return all detected architectural smells.


## Project Structure

📄 `project`
📦 `regix` (6 functions, 1 classes)
📦 `regix.backends` (6 functions, 1 classes)
📄 `regix.backends.architecture_backend` (3 functions, 1 classes)
📄 `regix.backends.coverage_backend` (5 functions, 1 classes)
📄 `regix.backends.docstring_backend` (3 functions, 1 classes)
📄 `regix.backends.lizard_backend` (3 functions, 1 classes)
📄 `regix.backends.radon_backend` (3 functions, 1 classes)
📄 `regix.backends.structure_backend` (7 functions, 2 classes)
📄 `regix.backends.vallm_backend` (3 functions, 1 classes)
📄 `regix.cache` (5 functions)
📄 `regix.cli` (8 functions)
📄 `regix.compare` (2 functions)
📄 `regix.config` (8 functions, 1 classes)
📄 `regix.exceptions` (4 functions, 5 classes)
📄 `regix.gates` (1 functions)
📄 `regix.git` (7 functions, 1 classes)
📄 `regix.history` (2 functions)
📦 `regix.integrations` (2 functions, 1 classes)
📄 `regix.models` (8 functions, 13 classes)
📄 `regix.report` (3 functions)
📄 `regix.smells` (8 functions)
📄 `regix.snapshot` (3 functions)
📄 `scripts.check_regression` (3 functions)

## Requirements

- Python >= >=3.9
- pyyaml >=6.0- typer >=0.12- rich >=13.0

## Contributing

**Contributors:**
- Tom Softreck <tom@sapletta.com>
- Tom Sapletta <tom-sapletta-com@users.noreply.github.com>

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/semcod/regix
cd regix

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Documentation

- 📖 [Full Documentation](https://github.com/semcod/regix/tree/main/docs) — API reference, module docs, architecture
- 🚀 [Getting Started](https://github.com/semcod/regix/blob/main/docs/getting-started.md) — Quick start guide
- 📚 [API Reference](https://github.com/semcod/regix/blob/main/docs/api.md) — Complete API documentation
- 🔧 [Configuration](https://github.com/semcod/regix/blob/main/docs/configuration.md) — Configuration options
- 💡 [Examples](./examples) — Usage examples and code samples

### Generated Files

| Output | Description | Link |
|--------|-------------|------|
| `README.md` | Project overview (this file) | — |
| `docs/api.md` | Consolidated API reference | [View](./docs/api.md) |
| `docs/modules.md` | Module reference with metrics | [View](./docs/modules.md) |
| `docs/architecture.md` | Architecture with diagrams | [View](./docs/architecture.md) |
| `docs/dependency-graph.md` | Dependency graphs | [View](./docs/dependency-graph.md) |
| `docs/coverage.md` | Docstring coverage report | [View](./docs/coverage.md) |
| `docs/getting-started.md` | Getting started guide | [View](./docs/getting-started.md) |
| `docs/configuration.md` | Configuration reference | [View](./docs/configuration.md) |
| `docs/api-changelog.md` | API change tracking | [View](./docs/api-changelog.md) |
| `CONTRIBUTING.md` | Contribution guidelines | [View](./CONTRIBUTING.md) |
| `examples/` | Usage examples | [Browse](./examples) |
| `mkdocs.yml` | MkDocs configuration | — |

<!-- code2docs:end -->