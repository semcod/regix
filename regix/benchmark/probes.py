from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from .models import BenchmarkResult


class BenchmarkProbe(ABC):
    suite: str = "custom"

    @abstractmethod
    def run(self) -> BenchmarkResult: ...


class ImportProbe(BenchmarkProbe):
    suite = "startup"

    def __init__(
        self,
        module: str,
        label: Optional[str] = None,
        threshold: Optional[float] = None,
        repeat: int = 3,
    ):
        self.module, self.label, self.threshold, self.repeat = (
            module,
            label or f"import {module}",
            threshold,
            repeat,
        )

    def run(self) -> BenchmarkResult:
        # ... (implementation logic from original file)
        pass


class CLIProbe(BenchmarkProbe):
    suite = "cli"

    def __init__(
        self,
        command: List[str],
        label: Optional[str] = None,
        cwd: Optional[Path] = None,
        threshold: Optional[float] = None,
        repeat: int = 3,
        env: Optional[Dict[str, str]] = None,
    ):
        self.command, self.label, self.cwd, self.threshold, self.repeat, self.env = (
            command,
            label or " ".join(command),
            cwd,
            threshold,
            repeat,
            env,
        )

    def run(self) -> BenchmarkResult:
        # ... (implementation logic from original file)
        pass


class UnitTestProbe(BenchmarkProbe):
    suite = "tests"

    def __init__(
        self,
        test_path: Path,
        label: Optional[str] = None,
        pytest_args: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        cwd: Optional[Path] = None,
    ):
        self.test_path, self.label, self.pytest_args, self.threshold, self.cwd = (
            test_path,
            label or f"pytest {test_path}",
            pytest_args or ["-q", "--tb=no", "--no-header"],
            threshold,
            cwd,
        )

    def run(self) -> BenchmarkResult:
        # ... (implementation logic from original file)
        pass
