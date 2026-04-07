"""Core data models — SymbolMetrics, Snapshot, Regression, Report, etc."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import yaml

@dataclass
class SymbolMetrics:
    """All tracked metrics for a single symbol (function, class, or module)."""
    file: str
    symbol: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    cc: float | None = None
    mi: float | None = None
    length: int | None = None
    coverage: float | None = None
    docstring_coverage: float | None = None
    quality_score: float | None = None
    imports: int | None = None
    fan_out: int | None = None
    call_count: int | None = None
    symbol_count: int | None = None
    param_count: int | None = None
    node_type_diversity: int | None = None
    logic_density: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricDelta:
    """Change in a single metric between two snapshots."""
    metric: str
    before: float | None
    after: float | None
    delta: float | None
    is_regression: bool
    is_improvement: bool
    severity: str
    threshold: float | None

@dataclass
class ArchSmell:
    """An architectural regression smell detected by cross-symbol analysis."""
    smell: str
    file: str
    symbol: str | None
    line: int | None
    severity: str
    detail: str
    ref_before: str = ''
    ref_after: str = ''

@dataclass
class Regression:
    """A detected worsening of a metric between two snapshots."""
    file: str
    symbol: str | None
    line: int | None
    metric: str
    before: float
    after: float
    delta: float
    severity: str
    threshold: float
    ref_before: str = ''
    ref_after: str = ''

@dataclass
class Improvement:
    """A detected improvement of a metric between two snapshots."""
    file: str
    symbol: str | None
    line: int | None
    metric: str
    before: float
    after: float
    delta: float
    ref_before: str = ''
    ref_after: str = ''

@dataclass
class Snapshot:
    """Immutable record of all SymbolMetrics for a codebase at a point in time."""
    ref: str
    commit_sha: str | None
    timestamp: datetime
    workdir: str
    symbols: list[SymbolMetrics] = field(default_factory=list)
    backend_versions: dict[str, str] = field(default_factory=dict)

    @property
    def metrics(self) -> dict[str, dict[str | None, SymbolMetrics]]:
        """Nested dict: metrics[file][symbol] → SymbolMetrics."""
        result: dict[str, dict[str | None, SymbolMetrics]] = {}
        for sm in self.symbols:
            result.setdefault(sm.file, {})[sm.symbol] = sm
        return result

    def get(self, file: str, symbol: str | None=None) -> SymbolMetrics | None:
        """Look up metrics for a specific file and optional symbol."""
        for sm in self.symbols:
            if sm.file == file and sm.symbol == symbol:
                return sm
        return None

    def save(self, path: str | Path) -> None:
        """Serialise snapshot to JSON."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {'ref': self.ref, 'commit_sha': self.commit_sha, 'timestamp': self.timestamp.isoformat(), 'workdir': str(self.workdir), 'backend_versions': self.backend_versions, 'symbols': [asdict(s) for s in self.symbols]}
        p.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')

    @classmethod
    def load(cls, path: str | Path) -> Snapshot:
        """Deserialise from JSON."""
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        symbols = [SymbolMetrics(**s) for s in data.get('symbols', [])]
        return cls(ref=data['ref'], commit_sha=data.get('commit_sha'), timestamp=datetime.fromisoformat(data['timestamp']), workdir=data.get('workdir', '.'), backend_versions=data.get('backend_versions', {}), symbols=symbols)

@dataclass
class RegressionReport:
    """Aggregated result of a comparison between two snapshots."""
    ref_before: str
    ref_after: str
    snapshot_before: Snapshot
    snapshot_after: Snapshot
    regressions: list[Regression] = field(default_factory=list)
    improvements: list[Improvement] = field(default_factory=list)
    smells: list[ArchSmell] = field(default_factory=list)
    unchanged: int = 0
    errors: int = 0
    warnings: int = 0
    smell_errors: int = 0
    smell_warnings: int = 0
    stagnated: bool = False
    duration: float = 0.0

    @property
    def has_errors(self) -> bool:
        return self.errors > 0

    @property
    def has_regressions(self) -> bool:
        return len(self.regressions) > 0

    @property
    def passed(self) -> bool:
        return self.errors == 0 and self.smell_errors == 0

    @property
    def summary(self) -> str:
        parts = [f'{self.errors} error(s)', f'{self.warnings} warning(s)', f'{len(self.improvements)} improvement(s)']
        if self.smells:
            parts.append(f'{len(self.smells)} smell(s)')
        status = 'PASS' if self.passed else 'FAIL'
        return f"Regression Report: {self.ref_before} → {self.ref_after}  [{status}]  {', '.join(parts)}"

    def to_dict(self) -> dict[str, Any]:
        return {'regix_schema_version': '1', 'ref_before': self.ref_before, 'ref_after': self.ref_after, 'errors': self.errors, 'warnings': self.warnings, 'smell_errors': self.smell_errors, 'smell_warnings': self.smell_warnings, 'improvements': len(self.improvements), 'unchanged': self.unchanged, 'stagnated': self.stagnated, 'duration': round(self.duration, 3), 'regressions': [asdict(r) for r in self.regressions], 'improvements_list': [asdict(i) for i in self.improvements], 'architectural_smells': [asdict(s) for s in self.smells]}

    def to_json(self, indent: int=2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @staticmethod
    def _toon_regression_section(label: str, items: list[Regression]) -> list[str]:
        """Format a TOON section for regressions (ERRORS or WARNINGS)."""
        if not items:
            return []
        lines = [f'{label}[{len(items)}]{{file,symbol,metric,before,after,delta}}:']
        for r in items:
            sign = '+' if r.delta > 0 else ''
            lines.append(f"  {r.file},{r.symbol or '(module)'},{r.metric},{r.before},{r.after},{sign}{r.delta}")
        lines.append('')
        return lines

    @staticmethod
    def _toon_smell_section(label: str, items: list[ArchSmell]) -> list[str]:
        """Format a TOON section for architectural smells."""
        if not items:
            return []
        lines = [f'{label}[{len(items)}]{{file,symbol,smell,detail}}:']
        for s in items:
            lines.append(f"  {s.file},{s.symbol or '(module)'},{s.smell},{s.detail}")
        lines.append('')
        return lines

    def to_toon(self) -> str:
        """TOON format — machine-readable plain text."""
        lines: list[str] = []
        status = f'{self.errors}e {self.warnings}w {len(self.improvements)}i'
        ts = datetime.now().strftime('%Y-%m-%d')
        lines.append(f'# regix compare | {self.ref_before} → {self.ref_after} | {status} | {ts}')
        lines.append('')
        total_symbols = len(self.regressions) + len(self.improvements) + self.unchanged
        lines.append('SUMMARY:')
        lines.append(f'  compared: {total_symbols} symbols  errors: {self.errors}  warnings: {self.warnings}  improvements: {len(self.improvements)}')
        lines.append('')
        errs = [r for r in self.regressions if r.severity == 'error']
        warns = [r for r in self.regressions if r.severity == 'warning']
        smell_errs = [s for s in self.smells if s.severity == 'error']
        smell_warns = [s for s in self.smells if s.severity == 'warning']
        lines.extend(self._toon_regression_section('ERRORS', errs))
        lines.extend(self._toon_smell_section('SMELL_ERRORS', smell_errs))
        lines.extend(self._toon_smell_section('SMELL_WARNINGS', smell_warns))
        lines.extend(self._toon_regression_section('WARNINGS', warns))
        if self.improvements:
            lines.append(f'IMPROVEMENTS[{len(self.improvements)}]{{file,symbol,metric,before,after,delta}}:')
            for i in self.improvements:
                sign = '+' if i.delta > 0 else ''
                lines.append(f"  {i.file},{i.symbol or '(module)'},{i.metric},{i.before},{i.after},{sign}{i.delta}")
            lines.append('')
        return '\n'.join(lines)

    def filter(self, file: str | None=None, symbol: str | None=None, metric: str | None=None, severity: str | None=None) -> RegressionReport:
        """Return a filtered copy of this report."""

        def _match_reg(r: Regression) -> bool:
            if file and r.file != file:
                return False
            if symbol and r.symbol != symbol:
                return False
            if metric and r.metric != metric:
                return False
            if severity and r.severity != severity:
                return False
            return True

        def _match_imp(i: Improvement) -> bool:
            if file and i.file != file:
                return False
            if symbol and i.symbol != symbol:
                return False
            if metric and i.metric != metric:
                return False
            return True

        def _match_smell(s: ArchSmell) -> bool:
            if file and s.file != file:
                return False
            if symbol and s.symbol != symbol:
                return False
            return True
        filtered_reg = [r for r in self.regressions if _match_reg(r)]
        filtered_imp = [i for i in self.improvements if _match_imp(i)]
        filtered_smells = [s for s in self.smells if _match_smell(s)]
        return RegressionReport(ref_before=self.ref_before, ref_after=self.ref_after, snapshot_before=self.snapshot_before, snapshot_after=self.snapshot_after, regressions=filtered_reg, improvements=filtered_imp, smells=filtered_smells, unchanged=self.unchanged, errors=sum((1 for r in filtered_reg if r.severity == 'error')), warnings=sum((1 for r in filtered_reg if r.severity == 'warning')), smell_errors=sum((1 for s in filtered_smells if s.severity == 'error')), smell_warnings=sum((1 for s in filtered_smells if s.severity == 'warning')), stagnated=self.stagnated, duration=self.duration)

@dataclass
class CommitMetrics:
    """Aggregated metrics for a single commit."""
    sha: str
    ref: str | None
    timestamp: datetime
    author: str
    message: str
    metrics: dict[str, float] = field(default_factory=dict)

@dataclass
class HistoryRegression:
    """A regression spanning multiple commits."""
    sha_start: str
    sha_end: str
    file: str
    symbol: str | None
    metric: str
    value_before: float
    value_worst: float
    value_current: float
    commits_affected: int

@dataclass
class TrendLine:
    """Linear trend across commit history for a single metric."""
    metric: str
    values: list[float] = field(default_factory=list)
    slope: float = 0.0
    is_degrading: bool = False

@dataclass
class HistoryReport:
    """Multi-commit metric timeline."""
    commits: list[CommitMetrics] = field(default_factory=list)
    regressions: list[HistoryRegression] = field(default_factory=list)
    trends: dict[str, TrendLine] = field(default_factory=dict)

@dataclass
class GateCheck:
    """Single gate threshold check."""
    metric: str
    value: float
    threshold: float
    operator: str
    passed: bool
    source: str = 'snapshot'
    severity: str = 'error'

@dataclass
class GateResult:
    """Aggregate gate evaluation result."""
    checks: list[GateCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """True when all hard-gates pass (ignores target-gate warnings)."""
        return not any((not c.passed and c.severity == 'error' for c in self.checks))

    @property
    def errors(self) -> list[GateCheck]:
        """Hard-gate violations that block the pipeline."""
        return [c for c in self.checks if not c.passed and c.severity == 'error']

    @property
    def warnings(self) -> list[GateCheck]:
        """Target-gate misses — reported but do not block."""
        return [c for c in self.checks if not c.passed and c.severity == 'warning']