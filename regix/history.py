"""History — multi-commit metric timeline builder."""

from __future__ import annotations

from pathlib import Path

from regix.config import RegressionConfig
from regix.git import list_commits
from regix.models import (
    CommitMetrics,
    HistoryReport,
    HistoryRegression,
    TrendLine,
)


def build_history(
    depth: int,
    ref: str,
    workdir: Path,
    config: RegressionConfig,
    metrics_filter: list[str] | None = None,
) -> HistoryReport:
    """Walk ``depth`` commits and return a HistoryReport with metric timeline."""
    from regix.snapshot import capture

    commits_info = list_commits(ref=ref, depth=depth, workdir=workdir)
    commit_metrics_list: list[CommitMetrics] = []

    for ci in commits_info:
        try:
            snap = capture(ci.sha, workdir, config)
        except Exception:
            continue

        # Aggregate metrics across all symbols
        cc_values: list[float] = []
        mi_values: list[float] = []
        cov_values: list[float] = []
        for sm in snap.symbols:
            if sm.cc is not None:
                cc_values.append(sm.cc)
            if sm.mi is not None:
                mi_values.append(sm.mi)
            if sm.coverage is not None:
                cov_values.append(sm.coverage)

        agg: dict[str, float] = {}
        if cc_values:
            agg["cc_avg"] = round(sum(cc_values) / len(cc_values), 2)
            agg["cc_max"] = max(cc_values)
        if mi_values:
            agg["mi_avg"] = round(sum(mi_values) / len(mi_values), 2)
        if cov_values:
            agg["coverage"] = round(sum(cov_values) / len(cov_values), 2)

        cm = CommitMetrics(
            sha=ci.sha,
            ref=None,
            timestamp=ci.timestamp,
            author=ci.author,
            message=ci.message,
            metrics=agg,
        )
        commit_metrics_list.append(cm)

    # Compute trends
    trends: dict[str, TrendLine] = {}
    metric_keys = metrics_filter or ["cc_avg", "cc_max", "mi_avg", "coverage"]
    for mk in metric_keys:
        values = [cm.metrics.get(mk, 0.0) for cm in commit_metrics_list]
        if len(values) >= 2:
            slope = _linear_slope(values)
            # For cc/length: positive slope = degrading; for mi/coverage: negative = degrading
            lower_better = mk.startswith("cc") or mk.startswith("length")
            is_degrading = (slope > 0 and lower_better) or (slope < 0 and not lower_better)
            trends[mk] = TrendLine(
                metric=mk, values=values, slope=round(slope, 4), is_degrading=is_degrading
            )

    return HistoryReport(
        commits=commit_metrics_list,
        regressions=[],  # TODO: detect multi-commit regressions
        trends=trends,
    )


def _linear_slope(values: list[float]) -> float:
    """Compute linear regression slope over an index series."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    var = sum((x - x_mean) ** 2 for x in xs)
    if var == 0:
        return 0.0
    return cov / var
