"""Gate evaluator — check a snapshot against absolute thresholds."""

from __future__ import annotations

from regix.config import RegressionConfig
from regix.models import GateCheck, GateResult, Snapshot


def check_gates(snapshot: Snapshot, config: RegressionConfig) -> GateResult:
    """Evaluate absolute quality gates against a single snapshot.

    This answers "does this snapshot meet the configured standards?" —
    not "did it regress relative to a baseline?".
    """
    checks: list[GateCheck] = []

    # Gate map: (metric_attr, config_threshold_attr, operator)
    # "le" → value must be <= threshold;  "ge" → value must be >= threshold
    gate_defs = [
        ("cc", "cc_max", "le"),
        ("mi", "mi_min", "ge"),
        ("coverage", "coverage_min", "ge"),
        ("length", "length_max", "le"),
        ("docstring_coverage", "docstring_min", "ge"),
        ("quality_score", "quality_min", "ge"),
    ]

    for sm in snapshot.symbols:
        for metric_attr, config_attr, operator in gate_defs:
            value = getattr(sm, metric_attr)
            if value is None:
                continue
            threshold = getattr(config, config_attr)

            if operator == "le":
                passed = value <= threshold
            elif operator == "ge":
                passed = value >= threshold
            else:
                passed = value == threshold

            if not passed:
                checks.append(GateCheck(
                    metric=metric_attr,
                    value=value,
                    threshold=threshold,
                    operator=operator,
                    passed=False,
                    source="snapshot",
                ))

    return GateResult(checks=checks)
