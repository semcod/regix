"""Performance benchmark for regix.

Measures:
- Startup / import time
- CLI command latency (snapshot, compare, gates, history, status)
- Unit test suite execution time
- Backend throughput (lizard, radon, etc.)

Usage:
    python benchmark.py                    # run all suites
    python benchmark.py --suite startup    # only startup probes
    python benchmark.py --suite cli        # only CLI probes
    python benchmark.py --suite tests      # only test-time probes
    python benchmark.py --suite backends   # only backend throughput probes
    python benchmark.py --suite throughput  # only in-process throughput probes
    python benchmark.py --json             # JSON output
    python benchmark.py --threshold 5.0    # fail if any probe > 5s
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    _RICH = True
except ImportError:
    _RICH = False

@dataclass
class BenchmarkResult:
    name: str
    suite: str
    elapsed: float
    unit: str = 's'
    extra: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    threshold: Optional[float] = None

    @property
    def passed(self) -> bool:
        if self.error:
            return False
        if self.threshold is not None:
            return self.elapsed <= self.threshold
        return True

    @property
    def status(self) -> str:
        if self.error:
            return 'ERROR'
        if self.threshold is not None:
            return 'PASS' if self.elapsed <= self.threshold else 'FAIL'
        return 'OK'

    def to_dict(self) -> Dict[str, Any]:
        return {'name': self.name, 'suite': self.suite, 'elapsed': round(self.elapsed, 4), 'unit': self.unit, 'status': self.status, 'threshold': self.threshold, 'extra': self.extra, 'error': self.error}

class BenchmarkProbe(ABC):
    """Abstract benchmark probe."""
    suite: str = 'custom'

    @abstractmethod
    def run(self) -> BenchmarkResult:
        ...

class ImportProbe(BenchmarkProbe):
    """Measures import time of a Python module in a fresh process."""
    suite = 'startup'

    def __init__(self, module: str, label: Optional[str]=None, threshold: Optional[float]=None, repeat: int=3):
        self.module = module
        self.label = label or f'import {module}'
        self.threshold = threshold
        self.repeat = repeat

    def run(self) -> BenchmarkResult:
        times: List[float] = []
        error: Optional[str] = None
        for _ in range(self.repeat):
            cmd = [sys.executable, '-c', f'import {self.module}']
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(cmd, capture_output=True, timeout=30)
                elapsed = time.perf_counter() - t0
                if proc.returncode != 0:
                    error = proc.stderr.decode(errors='replace').strip()
                    break
                times.append(elapsed)
            except subprocess.TimeoutExpired:
                error = 'timeout after 30s'
                break
            except Exception as e:
                error = str(e)
                break
        if error or not times:
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error=error or 'no measurements', threshold=self.threshold)
        best = min(times)
        return BenchmarkResult(name=self.label, suite=self.suite, elapsed=best, threshold=self.threshold, extra={'repeat': self.repeat, 'all_times': [round(t, 4) for t in times]})

class CLIProbe(BenchmarkProbe):
    """Measures execution time of a shell command."""
    suite = 'cli'

    def __init__(self, command: List[str], label: Optional[str]=None, cwd: Optional[Path]=None, threshold: Optional[float]=None, repeat: int=3, env: Optional[Dict[str, str]]=None):
        self.command = command
        self.label = label or ' '.join(command)
        self.cwd = cwd or _ROOT
        self.threshold = threshold
        self.repeat = repeat
        self.env = env

    def run(self) -> BenchmarkResult:
        times: List[float] = []
        error: Optional[str] = None
        env = {**os.environ, **(self.env or {})}
        for _ in range(self.repeat):
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(self.command, capture_output=True, cwd=self.cwd, timeout=120, env=env)
                elapsed = time.perf_counter() - t0
                if proc.returncode not in (0, 1):
                    error = proc.stderr.decode(errors='replace').strip()[:200]
                    break
                times.append(elapsed)
            except FileNotFoundError:
                error = f'command not found: {self.command[0]}'
                break
            except subprocess.TimeoutExpired:
                error = 'timeout after 120s'
                break
            except Exception as e:
                error = str(e)
                break
        if error or not times:
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error=error or 'no measurements', threshold=self.threshold)
        best = min(times)
        return BenchmarkResult(name=self.label, suite=self.suite, elapsed=best, threshold=self.threshold, extra={'repeat': self.repeat, 'all_times': [round(t, 4) for t in times]})

class UnitTestProbe(BenchmarkProbe):
    """Runs a pytest test suite and measures total time."""
    suite = 'tests'

    def __init__(self, test_path: Path, label: Optional[str]=None, pytest_args: Optional[List[str]]=None, threshold: Optional[float]=None, cwd: Optional[Path]=None):
        self.test_path = test_path
        self.label = label or f'pytest {test_path}'
        self.pytest_args = pytest_args or ['-q', '--tb=no', '--no-header']
        self.threshold = threshold
        self.cwd = cwd or _ROOT

    def run(self) -> BenchmarkResult:
        cmd = [sys.executable, '-m', 'pytest', str(self.test_path), '--tb=no', '--no-header', '-q', '--no-cov', *self.pytest_args]
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=self.cwd, timeout=300)
            elapsed = time.perf_counter() - t0
        except subprocess.TimeoutExpired:
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error='timeout after 300s', threshold=self.threshold)
        except Exception as e:
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error=str(e), threshold=self.threshold)
        extra: Dict[str, Any] = {'returncode': proc.returncode}
        output = proc.stdout + proc.stderr
        for line in output.splitlines():
            if ' passed' in line or ' failed' in line or ' error' in line:
                extra['summary'] = line.strip()
                break
        error = None
        if proc.returncode not in (0, 1, 5):
            error = (proc.stderr or proc.stdout)[:300].strip()
        return BenchmarkResult(name=self.label, suite=self.suite, elapsed=elapsed, threshold=self.threshold, extra=extra, error=error)

class ThroughputProbe(BenchmarkProbe):
    """Measures throughput of a callable (operations/second)."""
    suite = 'throughput'

    def __init__(self, label: str, fn: Callable[[], Any], n: int=100, setup: Optional[Callable[[], None]]=None, teardown: Optional[Callable[[], None]]=None, threshold_ops: Optional[float]=None, threshold_s: Optional[float]=None):
        self.label = label
        self.fn = fn
        self.n = n
        self.setup = setup
        self.teardown = teardown
        self.threshold_ops = threshold_ops
        self.threshold_s = threshold_s

    def run(self) -> BenchmarkResult:
        if self.setup:
            self.setup()
        try:
            t0 = time.perf_counter()
            for _ in range(self.n):
                self.fn()
            elapsed = time.perf_counter() - t0
        except Exception as e:
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error=str(e))
        finally:
            if self.teardown:
                try:
                    self.teardown()
                except Exception:
                    pass
        ops_per_sec = self.n / elapsed if elapsed > 0 else float('inf')
        if self.threshold_s is not None:
            threshold = self.threshold_s
        elif self.threshold_ops is not None:
            threshold = self.n / self.threshold_ops
        else:
            threshold = None
        return BenchmarkResult(name=self.label, suite=self.suite, elapsed=elapsed, threshold=threshold, extra={'n': self.n, 'ops_per_sec': round(ops_per_sec, 1), 'avg_ms': round(elapsed / self.n * 1000, 3)})

class BackendProbe(BenchmarkProbe):
    """Measures a single regix backend's collect() throughput on synthetic files."""
    suite = 'backends'

    def __init__(self, backend_name: str, file_count: int=20, file_size_kb: float=1.0, threshold: Optional[float]=None, label: Optional[str]=None):
        self.backend_name = backend_name
        self.file_count = file_count
        self.file_size_kb = file_size_kb
        self.threshold = threshold
        self.label = label or f'backend {backend_name} ({file_count}×{file_size_kb}KB)'

    def _generate_files(self, tmpdir: Path) -> List[Path]:
        """Create synthetic Python files with various constructs."""
        template = textwrap.dedent('            import os\n            import sys\n            from pathlib import Path\n\n\n            def func_{n}_a(x, y):\n                """Docstring for func a."""\n                result = []\n                for i in range(x):\n                    if i % 2 == 0:\n                        result.append(i * y)\n                    else:\n                        result.append(i + y)\n                return result\n\n\n            def func_{n}_b(data):\n                total = 0\n                for item in data:\n                    total += item\n                return total / len(data) if data else 0\n\n\n            class Handler_{n}:\n                def __init__(self, config):\n                    self.config = config\n                    self._cache = {{}}\n\n                def process(self, value):\n                    if value in self._cache:\n                        return self._cache[value]\n                    result = self._compute(value)\n                    self._cache[value] = result\n                    return result\n\n                def _compute(self, value):\n                    return value * 2 + 1\n        ')
        files: List[Path] = []
        lines_needed = max(1, int(self.file_size_kb * 1024 / 40))
        for i in range(self.file_count):
            content = template.format(n=i)
            while len(content.encode()) < self.file_size_kb * 1024:
                content += f'\ndef extra_{i}_{len(content) % 1000}(x): return x + 1\n'
            fpath = tmpdir / f'mod_{i:03d}.py'
            fpath.write_text(content, encoding='utf-8')
            files.append(fpath.relative_to(tmpdir))
        return files

    def run(self) -> BenchmarkResult:
        import shutil
        try:
            from regix.backends import get_backend
            from regix.config import RegressionConfig
        except ImportError as e:
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error=f'import error: {e}', threshold=self.threshold)
        backend = get_backend(self.backend_name)
        if backend is None:
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error=f"backend '{self.backend_name}' not registered", threshold=self.threshold)
        if not backend.is_available():
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error=f"backend '{self.backend_name}' not available", threshold=self.threshold)
        tmpdir = Path(tempfile.mkdtemp(prefix='regix_bench_'))
        try:
            files = self._generate_files(tmpdir)
            cfg = RegressionConfig()
            sources: Dict[str, str] = {}
            for fpath in files:
                sources[str(fpath)] = (tmpdir / fpath).read_text(encoding='utf-8')
            t0 = time.perf_counter()
            result = backend.collect(tmpdir, files, cfg, sources=sources)
            elapsed = time.perf_counter() - t0
            files_per_sec = self.file_count / elapsed if elapsed > 0 else float('inf')
            symbols_found = len(result)
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=elapsed, threshold=self.threshold, extra={'backend': self.backend_name, 'files': self.file_count, 'symbols_found': symbols_found, 'files_per_sec': round(files_per_sec, 1)})
        except Exception as e:
            return BenchmarkResult(name=self.label, suite=self.suite, elapsed=0.0, error=str(e)[:200], threshold=self.threshold)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

class BenchmarkSuite:
    """Collects probes and runs them."""

    def __init__(self, name: str='benchmark'):
        self.name = name
        self._probes: List[BenchmarkProbe] = []

    def add(self, probe: BenchmarkProbe) -> 'BenchmarkSuite':
        self._probes.append(probe)
        return self

    def run(self, suite_filter: Optional[str]=None) -> List[BenchmarkResult]:
        probes = self._probes
        if suite_filter:
            probes = [p for p in probes if p.suite == suite_filter]
        results: List[BenchmarkResult] = []
        for probe in probes:
            result = probe.run()
            results.append(result)
        return results

def _fmt_time(s: float) -> str:
    if s < 0.001:
        return f'{s * 1000:.2f} ms'
    if s < 1.0:
        return f'{s * 1000:.1f} ms'
    return f'{s:.3f}  s'

class BenchmarkReporter:
    """Prints results as a rich table or plain text."""

    def __init__(self, results: List[BenchmarkResult]):
        self.results = results

    @staticmethod
    def _format_result_details(r: BenchmarkResult) -> str:
        """Build the details string for a single benchmark result."""
        if not r.extra and (not r.error):
            return ''
        if not r.extra:
            return f'[red]{r.error[:80]}[/red]' if r.error else ''
        _EXTRA_KEYS = (('ops_per_sec', 'ops/s'), ('files_per_sec', 'files/s'), ('symbols_found', 'symbols'), ('summary', None))
        parts = []
        for key, suffix in _EXTRA_KEYS:
            if key in r.extra:
                parts.append(f'{r.extra[key]} {suffix}' if suffix else r.extra[key])
        if r.error:
            parts.append(f'[red]{r.error[:60]}[/red]')
        return '  '.join(parts)

    def print_rich(self) -> None:
        console = Console()
        console.print()
        console.print(Panel.fit('[bold cyan]Regix Performance Benchmark[/bold cyan]'))
        suites: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            suites.setdefault(r.suite, []).append(r)
        _STATUS_COLORS = {'OK': 'green', 'PASS': 'green', 'FAIL': 'red', 'ERROR': 'bold red'}
        for suite_name, suite_results in suites.items():
            table = Table(title=f'[bold]{suite_name.upper()}[/bold]', box=box.SIMPLE_HEAVY, show_header=True, header_style='bold magenta')
            table.add_column('Probe', style='cyan', min_width=35)
            table.add_column('Time', justify='right', min_width=12)
            table.add_column('Threshold', justify='right', min_width=12)
            table.add_column('Status', justify='center', min_width=8)
            table.add_column('Details', style='dim')
            for r in suite_results:
                sc = _STATUS_COLORS.get(r.status, 'white')
                table.add_row(r.name, _fmt_time(r.elapsed) if not r.error else '—', _fmt_time(r.threshold) if r.threshold else '—', f'[{sc}]{r.status}[/{sc}]', self._format_result_details(r))
            console.print(table)
        total = len(self.results)
        passed = sum((1 for r in self.results if r.status in ('OK', 'PASS')))
        failed = sum((1 for r in self.results if r.status == 'FAIL'))
        errors = sum((1 for r in self.results if r.status == 'ERROR'))
        console.print(f'[bold]Total:[/bold] {total}  [green]OK/PASS: {passed}[/green]  [red]FAIL: {failed}[/red]  [bold red]ERROR: {errors}[/bold red]')
        console.print()

    def print_plain(self) -> None:
        suites: Dict[str, List[BenchmarkResult]] = {}
        for r in self.results:
            suites.setdefault(r.suite, []).append(r)
        for suite_name, suite_results in suites.items():
            print(f"\n{'=' * 65}")
            print(f'  {suite_name.upper()}')
            print(f"{'=' * 65}")
            print(f"  {'Probe':<40} {'Time':>10}  {'Status':>8}")
            print(f"  {'-' * 62}")
            for r in suite_results:
                t = _fmt_time(r.elapsed) if not r.error else '—'
                print(f'  {r.name:<40} {t:>10}  {r.status:>8}')
                if r.extra.get('summary'):
                    print(f"    → {r.extra['summary']}")
                if r.error:
                    print(f'    ! {r.error[:80]}')

    def print_json(self) -> None:
        print(json.dumps([r.to_dict() for r in self.results], indent=2))

    def print(self, fmt: str='auto') -> None:
        if fmt == 'json':
            self.print_json()
        elif fmt == 'plain' or not _RICH:
            self.print_plain()
        else:
            self.print_rich()

    def any_failed(self) -> bool:
        return any((r.status in ('FAIL', 'ERROR') for r in self.results))

def build_regix_suite() -> BenchmarkSuite:
    """Build the default regix benchmark suite."""
    suite = BenchmarkSuite('regix')
    suite.add(ImportProbe('regix', threshold=2.0))
    suite.add(ImportProbe('regix.cli', threshold=3.0))
    suite.add(ImportProbe('regix.snapshot', threshold=2.0))
    suite.add(ImportProbe('regix.compare', threshold=2.0))
    suite.add(ImportProbe('regix.config', threshold=1.0))
    suite.add(ImportProbe('regix.models', threshold=1.0))
    suite.add(ImportProbe('regix.backends', threshold=2.0))
    suite.add(CLIProbe([sys.executable, '-m', 'regix', '--help'], label='regix --help', threshold=3.0))
    suite.add(CLIProbe([sys.executable, '-m', 'regix', 'status'], label='regix status', threshold=5.0))
    suite.add(CLIProbe([sys.executable, '-m', 'regix', 'snapshot', 'HEAD', '--format', 'json'], label='regix snapshot HEAD', threshold=30.0))
    suite.add(CLIProbe([sys.executable, '-m', 'regix', 'compare', 'HEAD~1', 'HEAD', '--format', 'json'], label='regix compare HEAD~1 HEAD', threshold=60.0))
    suite.add(CLIProbe([sys.executable, '-m', 'regix', 'gates'], label='regix gates', threshold=30.0))
    tests_dir = _ROOT / 'tests'
    if tests_dir.exists():
        suite.add(UnitTestProbe(tests_dir, label='full test suite', threshold=60.0))
        for test_file in sorted(tests_dir.glob('test_*.py')):
            suite.add(UnitTestProbe(test_file, label=f'pytest {test_file.name}', threshold=30.0))
    for bk_name, thresh in [('structure', 5.0), ('docstring', 5.0), ('architecture', 10.0), ('lizard', 15.0), ('radon', 15.0)]:
        suite.add(BackendProbe(backend_name=bk_name, file_count=20, file_size_kb=1.0, threshold=thresh))
    suite.add(_make_config_parse_probe())
    suite.add(_make_snapshot_probe())
    suite.add(_make_compare_probe())
    suite.add(_make_gates_probe())
    return suite

def _make_config_parse_probe() -> ThroughputProbe:
    """Benchmark config parsing throughput."""
    _state: Dict[str, Any] = {}

    def setup() -> None:
        tmpdir = tempfile.mkdtemp(prefix='regix_bench_cfg_')
        cfg_path = Path(tmpdir) / 'regix.yaml'
        cfg_path.write_text(textwrap.dedent('            regix:\n              workdir: .\n              metrics:\n                cc_max: 15\n                mi_min: 20\n                coverage_min: 80\n              thresholds:\n                delta_warn: 2\n                delta_error: 5\n              backends:\n                cc: lizard\n                mi: radon\n              exclude:\n                - "tests/**"\n                - ".venv/**"\n        '), encoding='utf-8')
        _state['cfg_path'] = str(cfg_path)
        _state['tmpdir'] = tmpdir

    def fn() -> None:
        from regix.config import RegressionConfig
        RegressionConfig.from_file(_state['cfg_path'])

    def teardown() -> None:
        import shutil
        shutil.rmtree(_state.get('tmpdir', ''), ignore_errors=True)
    return ThroughputProbe(label='RegressionConfig.from_file()', fn=fn, n=100, setup=setup, teardown=teardown, threshold_ops=50.0)

def _make_snapshot_probe() -> ThroughputProbe:
    """Benchmark snapshot capture throughput on current HEAD."""
    _state: Dict[str, Any] = {}

    def setup() -> None:
        from regix.config import RegressionConfig
        try:
            cfg = RegressionConfig.from_file(_ROOT)
        except FileNotFoundError:
            cfg = RegressionConfig()
        cfg.workdir = str(_ROOT)
        _state['cfg'] = cfg
        _state['wd'] = _ROOT

    def fn() -> None:
        from regix.snapshot import capture
        capture('HEAD', _state['wd'], _state['cfg'])
    return ThroughputProbe(label='snapshot.capture(HEAD)', fn=fn, n=3, setup=setup, threshold_s=30.0)

def _make_compare_probe() -> ThroughputProbe:
    """Benchmark compare() throughput using two snapshots."""
    _state: Dict[str, Any] = {}

    def setup() -> None:
        from regix.config import RegressionConfig
        from regix.snapshot import capture
        try:
            cfg = RegressionConfig.from_file(_ROOT)
        except FileNotFoundError:
            cfg = RegressionConfig()
        cfg.workdir = str(_ROOT)
        _state['cfg'] = cfg
        _state['snap'] = capture('HEAD', _ROOT, cfg)

    def fn() -> None:
        from regix.compare import compare as do_compare
        do_compare(_state['snap'], _state['snap'], _state['cfg'])
    return ThroughputProbe(label='compare(HEAD, HEAD)', fn=fn, n=10, setup=setup, threshold_ops=5.0)

def _make_gates_probe() -> ThroughputProbe:
    """Benchmark check_gates() throughput."""
    _state: Dict[str, Any] = {}

    def setup() -> None:
        from regix.config import RegressionConfig
        from regix.snapshot import capture
        try:
            cfg = RegressionConfig.from_file(_ROOT)
        except FileNotFoundError:
            cfg = RegressionConfig()
        cfg.workdir = str(_ROOT)
        _state['cfg'] = cfg
        _state['snap'] = capture('HEAD', _ROOT, cfg)

    def fn() -> None:
        from regix.gates import check_gates
        check_gates(_state['snap'], _state['cfg'])
    return ThroughputProbe(label='check_gates(HEAD)', fn=fn, n=50, setup=setup, threshold_ops=20.0)

def benchmark_library(module: str, cli_commands: Optional[List[List[str]]]=None, test_path: Optional[Path]=None, threshold_import: float=2.0, threshold_cli: float=5.0, threshold_tests: float=60.0) -> BenchmarkSuite:
    """Build a benchmark suite for an arbitrary Python library.

    Returns a BenchmarkSuite ready to .run(). Useful for comparing regix
    performance against other tools.
    """
    suite = BenchmarkSuite(module)
    suite.add(ImportProbe(module, threshold=threshold_import))
    for cmd in cli_commands or []:
        suite.add(CLIProbe(cmd, threshold=threshold_cli))
    if test_path and test_path.exists():
        suite.add(UnitTestProbe(test_path, threshold=threshold_tests))
    return suite

def main() -> int:
    parser = argparse.ArgumentParser(description='Performance benchmark for regix', formatter_class=argparse.RawDescriptionHelpFormatter, epilog=textwrap.dedent('            Examples:\n              python benchmark.py                     # all suites\n              python benchmark.py --suite startup     # import probes only\n              python benchmark.py --suite cli         # CLI command probes\n              python benchmark.py --suite tests       # unit test probes\n              python benchmark.py --suite backends    # backend throughput\n              python benchmark.py --suite throughput  # in-process throughput\n              python benchmark.py --json              # JSON output\n        '))
    parser.add_argument('--suite', choices=['startup', 'cli', 'tests', 'backends', 'throughput'], default=None, help='Run only probes from this suite (default: all)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--plain', action='store_true', help='Plain text (no colours)')
    parser.add_argument('--threshold', type=float, default=None, metavar='SEC', help='Override all time thresholds')
    args = parser.parse_args()
    suite = build_regix_suite()
    results = suite.run(suite_filter=args.suite)
    if args.threshold is not None:
        for r in results:
            if r.unit == 's':
                r.threshold = args.threshold
    fmt = 'json' if args.json else 'plain' if args.plain else 'auto'
    reporter = BenchmarkReporter(results)
    reporter.print(fmt=fmt)
    return 1 if reporter.any_failed() else 0
if __name__ == '__main__':
    sys.exit(main())