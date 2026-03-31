"""Gate evaluator — check a snapshot against absolute thresholds."""

from __future__ import annotations

from regix.config import GATE_METRICS, RegressionConfig
from regix.models import GateCheck, GateResult, Snapshot


def _passes(value: float, threshold: float, operator: str) -> bool:
    """Return True when *value* satisfies the gate *operator*."""
    if operator == "le":
        return value <= threshold
    if operator == "ge":
        return value >= threshold
    return value == threshold


def check_gates(snapshot: Snapshot, config: RegressionConfig) -> GateResult:
    """Evaluate absolute quality gates against a single snapshot.

    Two tiers of thresholds are checked:
    - **Hard-gates** (``severity="error"``) — pipeline blockers.
    - **Target-gates** (``severity="warning"``) — aspirational goals,
      reported but never block.

    ``GateResult.all_passed`` only considers hard-gate errors.
    """
    checks: list[GateCheck] = []

    for sm in snapshot.symbols:
        for gate_key, model_attr, operator in GATE_METRICS:
            value = getattr(sm, model_attr)
            if value is None:
                continue

            hard_val = config.hard.get(gate_key)
            target_val = config.target.get(gate_key)

            if not _passes(value, hard_val, operator):
                checks.append(GateCheck(
                    metric=model_attr,
                    value=value,
                    threshold=hard_val,
                    operator=operator,
                    passed=False,
                    source="snapshot",
                    severity="error",
                ))
            elif not _passes(value, target_val, operator):
                checks.append(GateCheck(
                    metric=model_attr,
                    value=value,
                    threshold=target_val,
                    operator=operator,
                    passed=False,
                    source="snapshot",
                    severity="warning",
                ))

    return GateResult(checks=checks)
