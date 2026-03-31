"""Core comparison engine — produces RegressionReport from two Snapshots."""

from __future__ import annotations

import time

from regix.config import RegressionConfig
from regix.models import (
    Improvement,
    MetricDelta,
    Regression,
    RegressionReport,
    Snapshot,
    SymbolMetrics,
)
from regix.smells import detect_smells

# Metrics to compare, in order
_TRACKED_METRICS = ("cc", "mi", "coverage", "length", "docstring_coverage",
                    "quality_score", "imports",
                    "fan_out", "call_count", "symbol_count",
                    "logic_density", "node_type_diversity")


def _compute_delta(
    metric: str,
    before: float | None,
    after: float | None,
    config: RegressionConfig,
) -> MetricDelta | None:
    """Compute a MetricDelta for a single metric between two values."""
    if before is None and after is None:
        return None
    if before is None or after is None:
        return None  # New or deleted symbol — handled separately

    delta = after - before
    lower_better = config.is_lower_better(metric)
    warn_thresh, error_thresh = config.delta_thresholds(metric)

    # For "lower is better" metrics: positive delta = regression
    # For "higher is better" metrics: negative delta = regression
    abs_delta = abs(delta)
    is_regression = (delta > 0 and lower_better) or (delta < 0 and not lower_better)
    is_improvement = (delta < 0 and lower_better) or (delta > 0 and not lower_better)

    if is_regression:
        if abs_delta >= error_thresh:
            severity = "error"
        elif abs_delta >= warn_thresh:
            severity = "warning"
        else:
            severity = "info"
    elif is_improvement:
        severity = "ok"
    else:
        severity = "ok"

    threshold = error_thresh if severity == "error" else warn_thresh

    return MetricDelta(
        metric=metric,
        before=before,
        after=after,
        delta=round(delta, 4),
        is_regression=is_regression,
        is_improvement=is_improvement,
        severity=severity,
        threshold=threshold,
    )


def _collect_deleted_symbol(
    m_before: SymbolMetrics,
    file_path: str,
    symbol_name: str | None,
    config: RegressionConfig,
    ref_before: str,
    ref_after: str,
) -> list[Improvement]:
    """Collect improvements for a deleted symbol."""
    result: list[Improvement] = []
    for metric in _TRACKED_METRICS:
        val = getattr(m_before, metric)
        if val is not None:
            result.append(Improvement(
                file=file_path,
                symbol=symbol_name,
                line=m_before.line_start,
                metric=metric,
                before=val,
                after=0.0,
                delta=-val if config.is_lower_better(metric) else val,
                ref_before=ref_before,
                ref_after=ref_after,
            ))
    return result


def _compare_symbol_metrics(
    m_before: SymbolMetrics,
    m_after: SymbolMetrics,
    file_path: str,
    symbol_name: str | None,
    config: RegressionConfig,
    ref_before: str,
    ref_after: str,
) -> tuple[list[Regression], list[Improvement], bool]:
    """Compare metrics for a single symbol between two snapshots."""
    regs: list[Regression] = []
    imps: list[Improvement] = []
    changed = False
    for metric in _TRACKED_METRICS:
        md = _compute_delta(metric, getattr(m_before, metric), getattr(m_after, metric), config)
        if md is None:
            continue
        if md.is_regression and md.severity in ("error", "warning"):
            regs.append(Regression(
                file=file_path, symbol=symbol_name, line=m_after.line_start,
                metric=metric, before=md.before, after=md.after,  # type: ignore[arg-type]
                delta=md.delta, severity=md.severity,  # type: ignore[arg-type]
                threshold=md.threshold,  # type: ignore[arg-type]
                ref_before=ref_before, ref_after=ref_after,
            ))
            changed = True
        elif md.is_improvement:
            imps.append(Improvement(
                file=file_path, symbol=symbol_name, line=m_after.line_start,
                metric=metric, before=md.before, after=md.after,  # type: ignore[arg-type]
                delta=md.delta,  # type: ignore[arg-type]
                ref_before=ref_before, ref_after=ref_after,
            ))
            changed = True
    return regs, imps, changed


def compare(
    snap_before: Snapshot,
    snap_after: Snapshot,
    config: RegressionConfig,
) -> RegressionReport:
    """Compare two snapshots and produce a regression report."""
    t0 = time.monotonic()

    idx_before: dict[tuple[str, str | None], SymbolMetrics] = {
        (s.file, s.symbol): s for s in snap_before.symbols
    }
    idx_after: dict[tuple[str, str | None], SymbolMetrics] = {
        (s.file, s.symbol): s for s in snap_after.symbols
    }

    all_keys = set(idx_before.keys()) | set(idx_after.keys())
    regressions: list[Regression] = []
    improvements: list[Improvement] = []
    unchanged = 0

    for key in sorted(all_keys, key=lambda k: (k[0], k[1] or "")):
        m_before = idx_before.get(key)
        m_after = idx_after.get(key)
        file_path, symbol_name = key

        if m_before is None:
            continue
        if m_after is None:
            improvements.extend(_collect_deleted_symbol(
                m_before, file_path, symbol_name, config,
                snap_before.ref, snap_after.ref,
            ))
            continue

        regs, imps, changed = _compare_symbol_metrics(
            m_before, m_after, file_path, symbol_name, config,
            snap_before.ref, snap_after.ref,
        )
        regressions.extend(regs)
        improvements.extend(imps)
        if not changed:
            unchanged += 1

    errors = sum(1 for r in regressions if r.severity == "error")
    warnings = sum(1 for r in regressions if r.severity == "warning")
    smells = detect_smells(snap_before, snap_after, config)
    smell_errors = sum(1 for s in smells if s.severity == "error")
    smell_warnings = sum(1 for s in smells if s.severity == "warning")

    return RegressionReport(
        ref_before=snap_before.ref,
        ref_after=snap_after.ref,
        snapshot_before=snap_before,
        snapshot_after=snap_after,
        regressions=regressions,
        improvements=improvements,
        smells=smells,
        unchanged=unchanged,
        errors=errors,
        warnings=warnings,
        smell_errors=smell_errors,
        smell_warnings=smell_warnings,
        stagnated=False,
        duration=round(time.monotonic() - t0, 3),
    )
