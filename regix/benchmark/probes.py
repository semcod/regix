import os
import subprocess
import sys
import tempfile
import textwrap
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

from .models import BenchmarkResult

_ROOT = Path(__file__).resolve().parent.parent.parent
_PYTEST_ADDOPTS_DENYLIST = {
    "--cov",
    "--no-cov",
    "--cov-report",
    "--cov-config",
    "--cov-append",
    "--cov-branch",
    "--cov-context",
    "--cov-fail-under",
}


def _measurement_error(
    *,
    name: str,
    suite: str,
    threshold: float | None,
    error: str,
) -> BenchmarkResult:
    return BenchmarkResult(
        name=name,
        suite=suite,
        elapsed=0.0,
        error=error,
        threshold=threshold,
    )


class BenchmarkProbe(ABC):
    suite: str = "custom"

    @abstractmethod
    def run(self) -> BenchmarkResult: ...


class ImportProbe(BenchmarkProbe):
    suite = "startup"

    def __init__(
        self,
        module: str,
        label: str | None = None,
        threshold: float | None = None,
        repeat: int = 3,
    ):
        self.module = module
        self.label = label or f"import {module}"
        self.threshold = threshold
        self.repeat = repeat

    def run(self) -> BenchmarkResult:
        times: list[float] = []
        error: str | None = None
        for _ in range(self.repeat):
            cmd = [sys.executable, "-c", f"import {self.module}"]
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(cmd, capture_output=True, timeout=30)
                elapsed = time.perf_counter() - t0
                if proc.returncode != 0:
                    error = proc.stderr.decode(errors="replace").strip()
                    break
                times.append(elapsed)
            except subprocess.TimeoutExpired:
                error = "timeout after 30s"
                break
            except Exception as exc:
                error = str(exc)
                break

        if error or not times:
            return _measurement_error(
                name=self.label,
                suite=self.suite,
                threshold=self.threshold,
                error=error or "no measurements",
            )

        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=min(times),
            threshold=self.threshold,
            extra={"repeat": self.repeat, "all_times": [round(t, 4) for t in times]},
        )


class CLIProbe(BenchmarkProbe):
    suite = "cli"

    def __init__(
        self,
        command: list[str],
        label: str | None = None,
        cwd: Path | None = None,
        threshold: float | None = None,
        repeat: int = 3,
        env: dict[str, str] | None = None,
    ):
        self.command = command
        self.label = label or " ".join(command)
        self.cwd = cwd or _ROOT
        self.threshold = threshold
        self.repeat = repeat
        self.env = env

    def run(self) -> BenchmarkResult:
        times: list[float] = []
        error: str | None = None
        env = {**os.environ, **(self.env or {})}

        for _ in range(self.repeat):
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(
                    self.command,
                    capture_output=True,
                    cwd=self.cwd,
                    timeout=120,
                    env=env,
                )
                elapsed = time.perf_counter() - t0
                if proc.returncode not in (0, 1):
                    error = proc.stderr.decode(errors="replace").strip()[:200]
                    break
                times.append(elapsed)
            except FileNotFoundError:
                error = f"command not found: {self.command[0]}"
                break
            except subprocess.TimeoutExpired:
                error = "timeout after 120s"
                break
            except Exception as exc:
                error = str(exc)
                break

        if error or not times:
            return _measurement_error(
                name=self.label,
                suite=self.suite,
                threshold=self.threshold,
                error=error or "no measurements",
            )

        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=min(times),
            threshold=self.threshold,
            extra={"repeat": self.repeat, "all_times": [round(t, 4) for t in times]},
        )


class UnitTestProbe(BenchmarkProbe):
    suite = "tests"

    def __init__(
        self,
        test_path: Path,
        label: str | None = None,
        pytest_args: list[str] | None = None,
        threshold: float | None = None,
        cwd: Path | None = None,
    ):
        self.test_path = test_path
        self.label = label or f"pytest {test_path}"
        self.pytest_args = pytest_args or ["-q", "--tb=no", "--no-header"]
        self.threshold = threshold
        self.cwd = cwd or _ROOT

    @staticmethod
    def _pytest_env() -> dict[str, str]:
        env = dict(os.environ)
        addopts = env.get("PYTEST_ADDOPTS")
        if not addopts:
            return env

        cleaned: list[str] = []
        skip_next = False
        for opt in addopts.split():
            if skip_next:
                skip_next = False
                continue
            name = opt.split("=", 1)[0]
            if name in _PYTEST_ADDOPTS_DENYLIST:
                skip_next = "=" not in opt and name in {
                    "--cov",
                    "--cov-report",
                    "--cov-config",
                    "--cov-context",
                    "--cov-fail-under",
                }
                continue
            cleaned.append(opt)
        if cleaned:
            env["PYTEST_ADDOPTS"] = " ".join(cleaned)
        else:
            env.pop("PYTEST_ADDOPTS", None)
        return env

    def run(self) -> BenchmarkResult:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(self.test_path),
            *self.pytest_args,
        ]
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=300,
                env=self._pytest_env(),
            )
            elapsed = time.perf_counter() - t0
        except subprocess.TimeoutExpired:
            return _measurement_error(
                name=self.label,
                suite=self.suite,
                threshold=self.threshold,
                error="timeout after 300s",
            )
        except Exception as exc:
            return _measurement_error(
                name=self.label,
                suite=self.suite,
                threshold=self.threshold,
                error=str(exc),
            )

        extra: dict[str, Any] = {"returncode": proc.returncode}
        output = proc.stdout + proc.stderr
        for line in output.splitlines():
            if " passed" in line or " failed" in line or " error" in line:
                extra["summary"] = line.strip()
                break

        error = None
        if proc.returncode not in (0, 1, 5):
            error = (proc.stderr or proc.stdout)[:300].strip()

        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=elapsed,
            threshold=self.threshold,
            extra=extra,
            error=error,
        )


class ThroughputProbe(BenchmarkProbe):
    """Measures throughput of a callable (operations/second)."""

    suite = "throughput"

    def __init__(
        self,
        label: str,
        fn: Callable[[], Any],
        n: int = 100,
        setup: Callable[[], None] | None = None,
        teardown: Callable[[], None] | None = None,
        threshold_ops: float | None = None,
        threshold_s: float | None = None,
    ):
        self.label = label
        self.fn = fn
        self.n = int(n)
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
        except Exception as exc:
            return BenchmarkResult(
                name=self.label,
                suite=self.suite,
                elapsed=0.0,
                error=str(exc),
            )
        finally:
            if self.teardown:
                try:
                    self.teardown()
                except Exception:
                    pass

        ops_per_sec = self.n / elapsed if elapsed > 0 else float("inf")
        if self.threshold_s is not None:
            threshold = self.threshold_s
        elif self.threshold_ops is not None:
            threshold = self.n / self.threshold_ops
        else:
            threshold = None

        return BenchmarkResult(
            name=self.label,
            suite=self.suite,
            elapsed=elapsed,
            threshold=threshold,
            extra={
                "n": self.n,
                "ops_per_sec": round(ops_per_sec, 1),
                "avg_ms": round(elapsed / self.n * 1000, 3),
            },
        )


class BackendProbe(BenchmarkProbe):
    """Measures a regix backend's collect() throughput on synthetic files."""

    suite = "backends"

    def __init__(
        self,
        backend_name: str,
        file_count: int = 20,
        file_size_kb: float = 1.0,
        threshold: float | None = None,
        label: str | None = None,
    ):
        self.backend_name = backend_name
        self.file_count = int(file_count)
        self.file_size_kb = file_size_kb
        self.threshold = threshold
        self.label = label or f"backend {backend_name} ({self.file_count}×{file_size_kb}KB)"

    def _generate_files(self, tmpdir: Path) -> list[Path]:
        template = textwrap.dedent(
            '            import os\n            import sys\n            from pathlib import Path\n\n\n            def func_{n}_a(x, y):\n                """Docstring for func a."""\n                result = []\n                for i in range(x):\n                    if i % 2 == 0:\n                        result.append(i * y)\n                    else:\n                        result.append(i + y)\n                return result\n\n\n            def func_{n}_b(data):\n                total = 0\n                for item in data:\n                    total += item\n                return total / len(data) if data else 0\n\n\n            class Handler_{n}:\n                def __init__(self, config):\n                    self.config = config\n                    self._cache = {{}}\n\n                def process(self, value):\n                    if value in self._cache:\n                        return self._cache[value]\n                    result = self._compute(value)\n                    self._cache[value] = result\n                    return result\n\n                def _compute(self, value):\n                    return value * 2 + 1\n        '
        )
        files: list[Path] = []
        for i in range(self.file_count):
            content = template.format(n=i)
            while len(content.encode()) < self.file_size_kb * 1024:
                content += f"\ndef extra_{i}_{len(content) % 1000}(x): return x + 1\n"
            fpath = tmpdir / f"mod_{i:03d}.py"
            fpath.write_text(content, encoding="utf-8")
            files.append(fpath.relative_to(tmpdir))
        return files

    def run(self) -> BenchmarkResult:
        import shutil

        try:
            from regix.backends import get_backend
            from regix.config import RegressionConfig
        except ImportError as exc:
            return _measurement_error(
                name=self.label,
                suite=self.suite,
                threshold=self.threshold,
                error=f"import error: {exc}",
            )

        backend = get_backend(self.backend_name)
        if backend is None:
            return _measurement_error(
                name=self.label,
                suite=self.suite,
                threshold=self.threshold,
                error=f"backend '{self.backend_name}' not registered",
            )
        if not backend.is_available():
            return BenchmarkResult(
                name=self.label,
                suite=self.suite,
                elapsed=0.0,
                threshold=self.threshold,
                skipped=True,
                extra={"summary": f"backend '{self.backend_name}' not available"},
            )

        tmpdir = Path(tempfile.mkdtemp(prefix="regix_bench_"))
        try:
            files = self._generate_files(tmpdir)
            cfg = RegressionConfig()
            sources = {
                str(fpath): (tmpdir / fpath).read_text(encoding="utf-8") for fpath in files
            }
            t0 = time.perf_counter()
            result = backend.collect(tmpdir, files, cfg, sources=sources)
            elapsed = time.perf_counter() - t0
            files_per_sec = self.file_count / elapsed if elapsed > 0 else float("inf")
            return BenchmarkResult(
                name=self.label,
                suite=self.suite,
                elapsed=elapsed,
                threshold=self.threshold,
                extra={
                    "backend": self.backend_name,
                    "files": self.file_count,
                    "symbols_found": len(result),
                    "files_per_sec": round(files_per_sec, 1),
                },
            )
        except Exception as exc:
            return _measurement_error(
                name=self.label,
                suite=self.suite,
                threshold=self.threshold,
                error=str(exc)[:200],
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
