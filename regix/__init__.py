"""Regix — Regression Index for Python code quality.

Detect, measure and report code quality regressions between git versions
at function, class and line granularity.
"""

from pathlib import Path

from regix.config import RegressionConfig
from regix.models import (
    ArchSmell,
    CommitMetrics,
    GateCheck,
    GateResult,
    HistoryRegression,
    HistoryReport,
    Improvement,
    MetricDelta,
    Regression,
    RegressionReport,
    Snapshot,
    SymbolMetrics,
    TrendLine,
)

# Ensure backends are registered on import
from regix.backends import docstring_backend as _docstring  # noqa: F401
from regix.backends import structure_backend as _structure  # noqa: F401
from regix.backends import architecture_backend as _architecture  # noqa: F401

try:
    from regix.backends import lizard_backend as _lizard  # noqa: F401
except ImportError:
    pass
try:
    from regix.backends import radon_backend as _radon  # noqa: F401
except ImportError:
    pass
try:
    from regix.backends import coverage_backend as _cov  # noqa: F401
except ImportError:
    pass
try:
    from regix.backends import vallm_backend as _vallm  # noqa: F401
except ImportError:
    pass


class Regix:
    """Main entry point — wraps snapshot, compare, and history."""

    def __init__(
        self,
        config: RegressionConfig | str | None = None,
        workdir: str = ".",
    ):
        if isinstance(config, str):
            self.config = RegressionConfig.from_file(config)
        elif config is None:
            try:
                self.config = RegressionConfig.from_file(workdir)
            except FileNotFoundError:
                self.config = RegressionConfig()
        else:
            self.config = config
        self.config.workdir = str(Path(workdir).resolve())
        self.config.apply_env_overrides()

    def snapshot(self, ref: str = "HEAD", use_cache: bool = True) -> Snapshot:
        """Capture metrics at a git ref."""
        from regix.snapshot import capture

        return capture(ref, Path(self.config.workdir), self.config)

    def compare(
        self,
        ref_before: str = "HEAD~1",
        ref_after: str = "HEAD",
        use_cache: bool = True,
    ) -> RegressionReport:
        """Compare metrics between two refs."""
        from regix.compare import compare as do_compare

        snap_a = self.snapshot(ref_before, use_cache)
        snap_b = self.snapshot(ref_after, use_cache)
        return do_compare(snap_a, snap_b, self.config)

    def compare_local(self, ref_before: str = "HEAD") -> RegressionReport:
        """Compare a git ref against the current working tree."""
        return self.compare(ref_before, "local", use_cache=False)

    def history(
        self,
        depth: int = 20,
        ref: str = "HEAD",
        metrics: list[str] | None = None,
    ) -> HistoryReport:
        """Walk commits and return a metric timeline."""
        from regix.history import build_history

        return build_history(
            depth=depth, ref=ref,
            workdir=Path(self.config.workdir),
            config=self.config,
            metrics_filter=metrics,
        )

    def check_gates(self, ref: str = "HEAD") -> GateResult:
        """Check current state against absolute thresholds."""
        from regix.gates import check_gates

        snap = self.snapshot(ref)
        return check_gates(snap, self.config)


__all__ = [
    "Regix",
    "RegressionConfig",
    "Snapshot",
    "SymbolMetrics",
    "MetricDelta",
    "Regression",
    "Improvement",
    "RegressionReport",
    "CommitMetrics",
    "HistoryRegression",
    "HistoryReport",
    "TrendLine",
    "GateCheck",
    "GateResult",
    "ArchSmell",
]

__version__ = "0.1.9"
