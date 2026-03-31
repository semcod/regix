"""Architectural smell detection — cross-symbol regression patterns.

Detects six categories of structural regressions that metric deltas alone miss:

  god_function       — one function absorbed others (function count dropped,
                       a single function grew disproportionately)
  stub_regression    — function shrank to a near-empty body with no calls
  no_delegation      — function previously delegating now has 0 calls + 0 params
  logic_density_drop — density of meaningful statements per line fell sharply
  cohesion_loss      — function body collapsed to a single statement type
  hallucination_proxy— multiple hollow-code signals fire simultaneously
"""

from __future__ import annotations

from regix.config import RegressionConfig
from regix.models import ArchSmell, Snapshot, SymbolMetrics


def detect_smells(
    snap_before: Snapshot,
    snap_after: Snapshot,
    config: RegressionConfig,
) -> list[ArchSmell]:
    """Compare two snapshots and return all detected architectural smells."""
    smells: list[ArchSmell] = []

    # Per-file symbol maps: symbol_name → SymbolMetrics (None symbol = module level)
    files_before = {s.file for s in snap_before.symbols}
    files_after = {s.file for s in snap_after.symbols}
    common_files = files_before & files_after

    for file in sorted(common_files):
        funcs_before: dict[str, SymbolMetrics] = {
            s.symbol: s
            for s in snap_before.symbols
            if s.file == file and s.symbol is not None
        }
        funcs_after: dict[str, SymbolMetrics] = {
            s.symbol: s
            for s in snap_after.symbols
            if s.file == file and s.symbol is not None
        }
        mod_before = next(
            (s for s in snap_before.symbols if s.file == file and s.symbol is None),
            None,
        )
        mod_after = next(
            (s for s in snap_after.symbols if s.file == file and s.symbol is None),
            None,
        )

        # ── God function (file-level) ─────────────────────────────────────────
        smells.extend(
            _check_god_function(
                file, funcs_before, funcs_after,
                mod_before, mod_after, config,
                snap_before.ref, snap_after.ref,
            )
        )

        # ── Per-symbol checks ─────────────────────────────────────────────────
        for sym, m_after in funcs_after.items():
            m_before = funcs_before.get(sym)

            if m_before is not None:
                s = _check_stub_regression(
                    file, sym, m_before, m_after, config,
                    snap_before.ref, snap_after.ref,
                )
                if s:
                    smells.append(s)

                s = _check_logic_density_drop(
                    file, sym, m_before, m_after, config,
                    snap_before.ref, snap_after.ref,
                )
                if s:
                    smells.append(s)

                s = _check_cohesion_loss(
                    file, sym, m_before, m_after, config,
                    snap_before.ref, snap_after.ref,
                )
                if s:
                    smells.append(s)

                s = _check_no_delegation(
                    file, sym, m_before, m_after, config,
                    snap_before.ref, snap_after.ref,
                )
                if s:
                    smells.append(s)

            s = _check_hallucination_proxy(
                file, sym, m_before, m_after, config,
                snap_before.ref, snap_after.ref,
            )
            if s:
                smells.append(s)

    return smells


# ── Helper ────────────────────────────────────────────────────────────────────


def _func_length(m: SymbolMetrics) -> int | None:
    """Best available function length: lizard nloc → AST span → None."""
    if m.length is not None:
        return m.length
    if m.line_start is not None and m.line_end is not None:
        return m.line_end - m.line_start + 1
    return None


# ── Smell detectors ───────────────────────────────────────────────────────────


def _check_god_function(
    file: str,
    funcs_before: dict[str, SymbolMetrics],
    funcs_after: dict[str, SymbolMetrics],
    mod_before: SymbolMetrics | None,
    mod_after: SymbolMetrics | None,
    config: RegressionConfig,
    ref_b: str,
    ref_a: str,
) -> list[ArchSmell]:
    """Detect when function count dropped and one function grew disproportionately."""
    fc_before = mod_before.raw.get("function_count") if mod_before else None
    fc_after = mod_after.raw.get("function_count") if mod_after else None

    if fc_before is None or fc_after is None:
        return []
    if fc_before <= 1 or fc_after >= fc_before:
        return []

    fc_dropped = fc_before - fc_after
    drop_ratio = fc_dropped / fc_before
    if drop_ratio < 0.30:
        return []

    # Average length of functions before
    lengths_before = [
        ln for m in funcs_before.values() if (ln := _func_length(m)) is not None
    ]
    if not lengths_before:
        return []
    avg_before = sum(lengths_before) / len(lengths_before)

    # Largest function in after snapshot
    candidates = [
        (sym, m) for sym, m in funcs_after.items()
        if _func_length(m) is not None
    ]
    if not candidates:
        return []
    largest_sym, largest_m = max(candidates, key=lambda t: _func_length(t[1]) or 0)
    largest_len = _func_length(largest_m) or 0

    if largest_len < config.god_func_length_min:
        return []
    if largest_len <= avg_before * 1.5:
        return []

    severity = (
        "error"
        if largest_len > avg_before * 2.5 or fc_dropped >= 2
        else "warning"
    )
    return [
        ArchSmell(
            smell="god_function",
            file=file,
            symbol=largest_sym,
            line=largest_m.line_start,
            severity=severity,
            detail=(
                f"Function count dropped {fc_before}→{fc_after} "
                f"({drop_ratio:.0%}); '{largest_sym}' is {largest_len} lines "
                f"(avg was {avg_before:.0f})"
            ),
            ref_before=ref_b,
            ref_after=ref_a,
        )
    ]


def _check_stub_regression(
    file: str,
    sym: str,
    m_before: SymbolMetrics,
    m_after: SymbolMetrics,
    config: RegressionConfig,
    ref_b: str,
    ref_a: str,
) -> ArchSmell | None:
    """Detect when a substantial function shrank to a near-empty stub."""
    len_b = _func_length(m_before)
    len_a = _func_length(m_after)
    calls_a = m_after.call_count

    if len_b is None or len_a is None or calls_a is None:
        return None
    if len_b <= config.stub_max_lines:
        return None  # Was already small — not a regression
    if len_a > config.stub_max_lines:
        return None
    if len_a / len_b > config.stub_shrink_ratio:
        return None  # Not enough shrinkage
    if calls_a > 0:
        return None  # Still has calls — not a hollow stub

    severity = "error" if len_a / len_b < 0.30 else "warning"
    return ArchSmell(
        smell="stub_regression",
        file=file,
        symbol=sym,
        line=m_after.line_start,
        severity=severity,
        detail=(
            f"Function shrank {len_b}→{len_a} lines "
            f"({len_a / len_b:.0%}) with no external calls"
        ),
        ref_before=ref_b,
        ref_after=ref_a,
    )


def _check_no_delegation(
    file: str,
    sym: str,
    m_before: SymbolMetrics,
    m_after: SymbolMetrics,
    config: RegressionConfig,
    ref_b: str,
    ref_a: str,
) -> ArchSmell | None:
    """Detect when a function that previously delegated work now has no calls or params."""
    calls_a = m_after.call_count
    params_a = m_after.param_count
    calls_b = m_before.call_count
    params_b = m_before.param_count

    if calls_a is None or params_a is None:
        return None
    if calls_a > 0 or params_a > 0:
        return None  # Still delegating

    len_a = _func_length(m_after)
    if len_a is not None and len_a > config.stub_max_lines * 2:
        return None  # Long body — might be pure computation, not a stub

    # Only a regression if it previously had delegation
    had_calls = calls_b is not None and calls_b > 0
    had_params = params_b is not None and params_b > 0
    if not had_calls and not had_params:
        return None  # Was always isolated — not a regression

    was_before = []
    if had_calls:
        was_before.append(f"{calls_b} call(s)")
    if had_params:
        was_before.append(f"{params_b} param(s)")

    return ArchSmell(
        smell="no_delegation",
        file=file,
        symbol=sym,
        line=m_after.line_start,
        severity="warning",
        detail=(
            f"'{sym}' lost all delegation: 0 params, 0 calls "
            f"(before: {', '.join(was_before)})"
        ),
        ref_before=ref_b,
        ref_after=ref_a,
    )


def _check_logic_density_drop(
    file: str,
    sym: str,
    m_before: SymbolMetrics,
    m_after: SymbolMetrics,
    config: RegressionConfig,
    ref_b: str,
    ref_a: str,
) -> ArchSmell | None:
    """Detect when statement density per line dropped below threshold."""
    ld_b = m_before.logic_density
    ld_a = m_after.logic_density

    if ld_b is None or ld_a is None:
        return None
    if ld_b < config.min_logic_density:
        return None  # Was already sparse — not a new regression
    if ld_a >= config.min_logic_density:
        return None  # Still acceptable

    drop = ld_b - ld_a
    severity = "error" if drop > 0.30 else "warning"
    return ArchSmell(
        smell="logic_density_drop",
        file=file,
        symbol=sym,
        line=m_after.line_start,
        severity=severity,
        detail=(
            f"Logic density dropped {ld_b:.2f}→{ld_a:.2f} "
            f"(min: {config.min_logic_density})"
        ),
        ref_before=ref_b,
        ref_after=ref_a,
    )


def _check_cohesion_loss(
    file: str,
    sym: str,
    m_before: SymbolMetrics,
    m_after: SymbolMetrics,
    config: RegressionConfig,
    ref_b: str,
    ref_a: str,
) -> ArchSmell | None:
    """Detect when function body collapsed to a single statement type."""
    div_b = m_before.node_type_diversity
    div_a = m_after.node_type_diversity

    if div_b is None or div_a is None:
        return None
    if div_b < config.min_node_diversity:
        return None  # Was already homogeneous
    if div_a >= config.min_node_diversity:
        return None  # Still diverse

    return ArchSmell(
        smell="cohesion_loss",
        file=file,
        symbol=sym,
        line=m_after.line_start,
        severity="warning",
        detail=(
            f"Node type diversity dropped {div_b}→{div_a} unique statement types "
            f"(min: {config.min_node_diversity})"
        ),
        ref_before=ref_b,
        ref_after=ref_a,
    )


def _check_hallucination_proxy(
    file: str,
    sym: str,
    m_before: SymbolMetrics | None,
    m_after: SymbolMetrics,
    config: RegressionConfig,
    ref_b: str,
    ref_a: str,
) -> ArchSmell | None:
    """Detect hollow/stub functions: zero calls + very low density + trivial CC.

    Only fires as a regression when the function was not already hollow before.
    """
    calls_a = m_after.call_count
    ld_a = m_after.logic_density
    len_a = _func_length(m_after)
    cc_a = m_after.cc

    if calls_a is None or ld_a is None:
        return None
    if calls_a > 0:
        return None  # Has external calls — not hollow

    # Require at least two hollow signals to avoid false positives
    hollow_signals = 0
    if len_a is not None and len_a <= config.hallucination_max_lines:
        hollow_signals += 1
    if ld_a < config.min_logic_density:
        hollow_signals += 1
    if cc_a is not None and cc_a <= 1:
        hollow_signals += 1

    if hollow_signals < 2:
        return None

    # Skip if it was already hollow before (only report regression)
    if m_before is not None:
        calls_b = m_before.call_count
        ld_b = m_before.logic_density
        len_b = _func_length(m_before)
        already_hollow = (
            (calls_b is None or calls_b == 0)
            and (ld_b is None or ld_b < config.min_logic_density)
            and (len_b is None or len_b <= config.hallucination_max_lines)
        )
        if already_hollow:
            return None

    return ArchSmell(
        smell="hallucination_proxy",
        file=file,
        symbol=sym,
        line=m_after.line_start,
        severity="warning",
        detail=(
            f"'{sym}': calls=0, density={ld_a:.2f}, "
            f"length={len_a or '?'}, cc={cc_a or '?'} — "
            "appears hollow (stub or placeholder)"
        ),
        ref_before=ref_b,
        ref_after=ref_a,
    )
