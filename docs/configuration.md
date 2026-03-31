# Regix — Configuration Reference

## Configuration file locations

Regix searches for configuration in the following order (first match wins):

1. Path passed explicitly via `--config FILE` or `Regix(config=path)`
2. `regix.yaml` in the current directory
3. `.regix/config.yaml` in the current directory
4. `pyproject.toml` — `[tool.regix]` section
5. `regix.yaml` in the git root (if `workdir` is inside a git repo)

If no configuration file is found, Regix uses built-in defaults.

---

## Full configuration reference

```yaml
regix:
  # ── Working directory ──────────────────────────────────────────────────────
  workdir: .                      # root of the project to analyse

  # ── Metric thresholds (absolute gate values) ───────────────────────────────
  #    Used by `regix gates` and the pyqual integration.
  #    NOT used for regression detection (which uses delta thresholds below).
  metrics:
    cc_max: 15                    # max cyclomatic complexity per function
    mi_min: 20                    # min maintainability index (0–100)
    coverage_min: 80              # min test coverage (%)
    length_max: 100               # max function body length (lines)
    docstring_min: 60             # min docstring coverage (%)
    quality_min: 0.85             # min vallm quality score (0–1)

  # ── Regression detection thresholds ────────────────────────────────────────
  #    A change must exceed these deltas to be reported.
  thresholds:
    delta_warn: 2                 # emit WARNING when |delta| >= this
    delta_error: 5                # emit ERROR when |delta| >= this

    # Per-metric overrides (optional, overrides the defaults above)
    per_metric:
      cc:
        delta_warn: 2
        delta_error: 5
      mi:
        delta_warn: 5             # MI is noisier, require a larger shift
        delta_error: 10
      coverage:
        delta_warn: 1             # even 1% coverage drop is a warning
        delta_error: 5
      length:
        delta_warn: 10
        delta_error: 25

  # ── File filtering ─────────────────────────────────────────────────────────
  #    Glob patterns relative to workdir.
  #    'include' takes precedence: if set, only matching files are analysed.
  #    'exclude' is applied after include.
  include:
    - "src/**/*.py"
    - "mypackage/**/*.py"
    # If empty (default), all .py files under workdir are included.

  exclude:
    - "tests/**"                  # test files skew CC metrics
    - "examples/**"               # examples are not production code
    - "docs/**"
    - "**/migrations/**"
    - "**/*_pb2.py"               # generated protobuf files
    - "build/**"
    - "dist/**"
    - ".venv/**"
    - "venv/**"

  # ── Analysis backends ──────────────────────────────────────────────────────
  backends:
    cc: lizard                    # lizard | radon | both
    mi: radon                     # radon only
    coverage: pytest-cov          # pytest-cov | none
    quality: vallm                # vallm | none
    docstring: builtin            # builtin (ast-based) | none

    # Run backends concurrently within a single snapshot capture
    parallel: false

  # ── Snapshot & cache ───────────────────────────────────────────────────────
  cache:
    enabled: true
    dir: ~/.cache/regix           # XDG_CACHE_HOME/regix if unset
    max_entries: 200              # evict oldest entries beyond this count
    max_size_mb: 500

  # ── Loop / stagnation behaviour ────────────────────────────────────────────
  #    Used when Regix is called in a retry loop (e.g., inside pyqual).
  loop:
    stagnation_window: 2          # break if report is identical for N iterations

  # ── Output ─────────────────────────────────────────────────────────────────
  output:
    format: rich                  # rich | json | yaml | toon
    dir: .regix/                  # directory for saved reports
    filename: report              # report.json / report.yaml / report.toon.yaml
    show_improvements: true       # include improvement entries in output
    max_symbols: 100              # truncate symbol list beyond this (0 = unlimited)
    color: auto                   # auto | always | never  (rich renderer only)

  # ── Gate behaviour ─────────────────────────────────────────────────────────
  gates:
    on_regression: warn           # warn | error | block
    #   warn  → exit 0, print warning
    #   error → exit 1 if any Regression with severity="error"
    #   block → exit 1 if any Regression regardless of severity
    fail_exit_code: 1
```

---

## `pyproject.toml` format

```toml
[tool.regix]
workdir = "."

[tool.regix.metrics]
cc_max = 15
mi_min = 20
coverage_min = 80
length_max = 100

[tool.regix.thresholds]
delta_warn = 2
delta_error = 5

[tool.regix.exclude]
patterns = ["tests/**", "examples/**", "docs/**"]

[tool.regix.backends]
cc = "lizard"
mi = "radon"
coverage = "pytest-cov"
quality = "vallm"

[tool.regix.output]
format = "rich"
dir = ".regix/"
show_improvements = true
```

---

## Environment variables

All configuration values can be overridden by environment variables. The naming convention is `REGIX_<SECTION>_<KEY>` in uppercase with dots replaced by underscores.

| Variable | Config key | Default |
|---|---|---|
| `REGIX_WORKDIR` | `regix.workdir` | `.` |
| `REGIX_CC_MAX` | `regix.metrics.cc_max` | `15` |
| `REGIX_MI_MIN` | `regix.metrics.mi_min` | `20` |
| `REGIX_COVERAGE_MIN` | `regix.metrics.coverage_min` | `80` |
| `REGIX_DELTA_WARN` | `regix.thresholds.delta_warn` | `2` |
| `REGIX_DELTA_ERROR` | `regix.thresholds.delta_error` | `5` |
| `REGIX_FORMAT` | `regix.output.format` | `rich` |
| `REGIX_OUTPUT_DIR` | `regix.output.dir` | `.regix/` |
| `REGIX_CACHE_ENABLED` | `regix.cache.enabled` | `true` |
| `REGIX_CACHE_DIR` | `regix.cache.dir` | `~/.cache/regix` |
| `REGIX_BACKEND_CC` | `regix.backends.cc` | `lizard` |
| `REGIX_BACKEND_MI` | `regix.backends.mi` | `radon` |
| `REGIX_BACKEND_COVERAGE` | `regix.backends.coverage` | `pytest-cov` |
| `REGIX_BACKEND_QUALITY` | `regix.backends.quality` | `vallm` |
| `REGIX_ON_REGRESSION` | `regix.gates.on_regression` | `warn` |
| `REGIX_FAIL_EXIT_CODE` | `regix.gates.fail_exit_code` | `1` |

---

## Common configurations

### Minimal — CC only, no coverage

```yaml
regix:
  metrics:
    cc_max: 15
  backends:
    cc: lizard
    mi: none
    coverage: none
    quality: none
    docstring: none
  exclude:
    - "tests/**"
    - "examples/**"
```

### Strict — all metrics, tight deltas

```yaml
regix:
  metrics:
    cc_max: 10
    mi_min: 40
    coverage_min: 90
    length_max: 50
    docstring_min: 80
  thresholds:
    delta_warn: 1
    delta_error: 3
  gates:
    on_regression: error
```

### CI-safe — fail on errors only, save JSON report

```yaml
regix:
  output:
    format: json
    dir: .regix/
  gates:
    on_regression: error
  cache:
    enabled: true
    dir: .regix/cache
```

CI workflow:

```yaml
- uses: actions/cache@v4
  with:
    path: .regix/cache
    key: regix-${{ runner.os }}-${{ hashFiles('**/*.py') }}

- run: regix compare ${{ github.base_ref }} HEAD --format json
- run: regix gates --fail-on error
```

### Monorepo — per-package configuration

```
myrepo/
├── packages/
│   ├── api/
│   │   └── regix.yaml     ← api-specific thresholds
│   └── core/
│       └── regix.yaml     ← core-specific thresholds
└── regix.yaml              ← defaults for the root
```

Run per-package:

```bash
regix compare HEAD~1 HEAD --config packages/api/regix.yaml
regix compare HEAD~1 HEAD --config packages/core/regix.yaml
```

Or from root (each package overrides via its local `regix.yaml`):

```bash
for pkg in packages/*/; do
  regix compare HEAD~1 HEAD --workdir "$pkg" --config "${pkg}regix.yaml"
done
```

### pyqual integration

```yaml
# pyqual.yaml
pipeline:
  metrics:
    cc_max: 15
    regression_errors_max: 0     # from Regix gate collector
    regression_warnings_max: 5

  stages:
    - name: analyze
      tool: code2llm
      when: first_iteration

    - name: validate
      run: vallm batch pyqual tests --recursive --format toon --output ./project
      when: always

    - name: regression-check
      tool: regix                 # runs: regix compare HEAD~1 HEAD --format toon --output .regix/
      when: always

    - name: test
      tool: pytest
      optional: true

    - name: fix
      run: llx fix . --apply --errors .pyqual/errors.json --verbose
      when: metrics_fail
      timeout: 1800
```

---

## Threshold tuning guide

### Starting values

If you are adding Regix to an existing project for the first time, run:

```bash
regix snapshot HEAD --format json > .regix/baseline.json
regix history --depth 20 --format json > .regix/history.json
```

Inspect the output to understand your current metric distribution before setting thresholds. Setting `cc_max: 15` on a codebase where the median function CC is 12 will generate noise; setting it at 25 will miss real regressions.

### Recommended starting point

| Metric | Conservative | Moderate | Strict |
|---|---|---|---|
| `cc_max` | 25 | 15 | 10 |
| `mi_min` | 10 | 20 | 40 |
| `coverage_min` | 60 | 80 | 90 |
| `length_max` | 150 | 100 | 50 |
| `delta_warn` | 5 | 2 | 1 |
| `delta_error` | 10 | 5 | 3 |

### Exclude test files

Test code legitimately has different metric characteristics than production code:
- Test functions are often long (arranging complex fixtures)
- CC in tests is often high (many assertions, parametrize)
- Maintainability index is less meaningful for test code

Always exclude `tests/` and `test_*.py` from regression tracking unless you specifically want to track test code quality.

### Handle generated code

Generated files (migrations, protobuf, OpenAPI clients) should always be excluded. They may have extremely high CC and near-zero MI, which would make every comparison noisy and meaningless.

```yaml
exclude:
  - "**/migrations/**"
  - "**/*_pb2.py"
  - "**/*_pb2_grpc.py"
  - "**/generated/**"
  - "**/*.generated.py"
```

---

## Metric definitions

### Cyclomatic Complexity (`cc`)

Counts the number of linearly independent paths through a function. Each `if`, `elif`, `for`, `while`, `except`, `with`, `assert`, `and`, `or` adds 1.

- **Source**: lizard (default) or radon
- **Direction**: lower is better
- **Typical range**: 1 (trivial) to 50+ (highly complex)
- **Recommended max**: 15 (McCabe's original threshold)

### Maintainability Index (`mi`)

A composite metric combining Halstead volume, cyclomatic complexity, and lines of code. Scores above 20 are considered maintainable.

- **Source**: radon
- **Direction**: higher is better
- **Range**: 0–100
- **Recommended min**: 20

Note: MI is computed at file level (not function level). A low MI for an entire module usually indicates the module is doing too much and should be split.

### Test Coverage (`coverage`)

Percentage of source lines executed during the test suite.

- **Source**: pytest-cov (reads `.coverage` file)
- **Direction**: higher is better
- **Range**: 0–100
- **Recommended min**: 80

Regix reports coverage at file level. For function-level coverage, enable branch coverage in pytest-cov (`--cov-report=json --cov-branch`).

### Function Length (`length`)

Number of lines in the function body (excluding blank lines and comments).

- **Source**: lizard
- **Direction**: lower is better
- **Recommended max**: 100

### LLM Quality Score (`quality_score`)

A 0–1 score from `vallm` representing the LLM's assessment of code quality for the file (documentation, naming, structure).

- **Source**: vallm
- **Direction**: higher is better
- **Range**: 0–1

### Docstring Coverage (`docstring_coverage`)

Percentage of public functions and classes that have a docstring.

- **Source**: built-in (`ast`)
- **Direction**: higher is better
- **Range**: 0–100

---

## Important lessons (from pyqual operational experience)

### Scan only the files you own

Running `vallm batch . --recursive` (or any analysis tool) on the entire project root will include:
- Documentation (`docs/`, `*.md`)
- Example code (`examples/`)
- Configuration files (`*.yaml`, `*.toml`)
- Generated code

These files are typically unsupported by static analysis tools and end up counted as "failures" in pass-rate calculations, producing a misleadingly low pass rate (e.g., 56/96 = 58.3% when scanning everything vs 56/57 = 98.2% when scanning only Python source).

**Always configure `include` or restrict the analysis to your source directories.**

### Absolute violations ≠ regressions

A function with CC=18 that had CC=18 last month is a **technical debt item** — it needs refactoring, but it is not a regression introduced by recent changes. Reporting it as a regression on every PR creates alert fatigue and causes developers to ignore the tool.

Regix separates these two concerns:
- `regix compare` reports **regressions** (delta-based, relative to a baseline)
- `regix gates` reports **absolute violations** (threshold-based, point-in-time)

Use both: `regix gates` in CI to prevent new absolute violations, and `regix compare` to catch regressions introduced by specific PRs.

### Use `--local` before committing

```bash
# Before committing: check if your changes caused any regressions
regix compare HEAD --local
```

This compares the committed `HEAD` against the current working tree. It catches regressions before they enter git history, which is much cheaper to fix.
