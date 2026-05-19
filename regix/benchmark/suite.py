"""Benchmark suite — collects and runs probes."""

from typing import List, Optional

from .models import BenchmarkResult
from .probes import BenchmarkProbe


class BenchmarkSuite:
    """Collects probes and runs them."""

    def __init__(self, name: str = "benchmark"):
        self.name = name
        self._probes: List[BenchmarkProbe] = []

    def add(self, probe: BenchmarkProbe) -> "BenchmarkSuite":
        self._probes.append(probe)
        return self

    def run(self, suite_filter: Optional[str] = None) -> List[BenchmarkResult]:
        probes = self._probes
        if suite_filter:
            probes = [p for p in probes if p.suite == suite_filter]
        results: List[BenchmarkResult] = []
        for probe in probes:
            result = probe.run()
            results.append(result)
        return results
