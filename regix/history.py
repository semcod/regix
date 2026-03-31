"""History — multi-commit metric timeline builder."""

from __future__ import annotations

from pathlib import Path

from regix.config import RegressionConfig
from regix.git import list_commits
from regix.models import (
    CommitMetrics,
    HistoryReport,
    TrendLine,
)


def _aggregate_snapshot_metrics(
    symbols: list,
) -> dict[str, float]:
    """Aggregate per-symbol metrics into summary stats."""
    buckets: dict[str, list[float]] = {"cc": [], "mi": [], "coverage": []}
    for sm in symbols:
        for key in buckets:
            val = getattr(sm, key, None)
            if val is not None:
                buckets[key].append(val)

    agg: dict[str, float] = {}
    if buckets["cc"]:
        agg["cc_avg"] = round(sum(buckets["cc"]) / len(buckets["cc"]), 2)
        agg["cc_max"] = max(buckets["cc"])
    if buckets["mi"]:
        agg["mi_avg"] = round(sum(buckets["mi"]) / len(buckets["mi"]), 2)
    if buckets["coverage"]:
        agg["coverage"] = round(sum(buckets["coverage"]) / len(buckets["coverage"]), 2)
    return agg


def _compute_trends(
    commit_metrics_list: list[CommitMetrics],
    metric_keys: list[str],
) -> dict[str, TrendLine]:
    """Compute linear trends for each metric across commits."""
    trends: dict[str, TrendLine] = {}
    for mk in metric_keys:
        values = [cm.metrics.get(mk, 0.0) for cm in commit_metrics_list]
        if len(values) < 2:
            continue
        slope = _linear_slope(values)
        lower_better = mk.startswith("cc") or mk.startswith("length")
        is_degrading = (slope > 0 and lower_better) or (slope < 0 and not lower_better)
        trends[mk] = TrendLine(
            metric=mk, values=values, slope=round(slope, 4), is_degrading=is_degrading,
        )
    return trends


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

        cm = CommitMetrics(
            sha=ci.sha, ref=None, timestamp=ci.timestamp,
            author=ci.author, message=ci.message,
            metrics=_aggregate_snapshot_metrics(snap.symbols),
        )
        commit_metrics_list.append(cm)

    metric_keys = metrics_filter or ["cc_avg", "cc_max", "mi_avg", "coverage"]
    return HistoryReport(
        commits=commit_metrics_list,
        regressions=[],
        trends=_compute_trends(commit_metrics_list, metric_keys),
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
