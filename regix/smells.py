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
from regix.config import RegressionConfig
from regix.models import ArchSmell, Snapshot, SymbolMetrics

def detect_smells(snap_before: Snapshot, snap_after: Snapshot, config: RegressionConfig) -> list[ArchSmell]:
    """Compare two snapshots and return all detected architectural smells."""
    smells: list[ArchSmell] = []
    files_before = {s.file for s in snap_before.symbols}
    files_after = {s.file for s in snap_after.symbols}
    common_files = files_before & files_after
    for file in sorted(common_files):
        funcs_before: dict[str, SymbolMetrics] = {s.symbol: s for s in snap_before.symbols if s.file == file and s.symbol is not None}
        funcs_after: dict[str, SymbolMetrics] = {s.symbol: s for s in snap_after.symbols if s.file == file and s.symbol is not None}
        mod_before = next((s for s in snap_before.symbols if s.file == file and s.symbol is None), None)
        mod_after = next((s for s in snap_after.symbols if s.file == file and s.symbol is None), None)
        smells.extend(_check_god_function(file, funcs_before, funcs_after, mod_before, mod_after, config, snap_before.ref, snap_after.ref))
        for sym, m_after in funcs_after.items():
            m_before = funcs_before.get(sym)
            smells.extend(_check_symbol_smells(file, sym, m_before, m_after, config, snap_before.ref, snap_after.ref))
    return smells

def _check_symbol_smells(file: str, sym: str, m_before: SymbolMetrics | None, m_after: SymbolMetrics, config: RegressionConfig, ref_b: str, ref_a: str) -> list[ArchSmell]:
    """Run all per-symbol smell checks and return detected smells."""
    results: list[ArchSmell] = []
    _PAIRED_CHECKS = (_check_stub_regression, _check_logic_density_drop, _check_cohesion_loss, _check_no_delegation)
    if m_before is not None:
        for check in _PAIRED_CHECKS:
            s = check(file, sym, m_before, m_after, config, ref_b, ref_a)
            if s:
                results.append(s)
    s = _check_hallucination_proxy(file, sym, m_before, m_after, config, ref_b, ref_a)
    if s:
        results.append(s)
    return results

def _func_length(m: SymbolMetrics) -> int | None:
    """Best available function length: lizard nloc → AST span → None."""
    if m.length is not None:
        return m.length
    if m.line_start is not None and m.line_end is not None:
        return m.line_end - m.line_start + 1
    return None

def _function_count_drop(mod_before: SymbolMetrics | None, mod_after: SymbolMetrics | None) -> tuple[int, int, float] | None:
    """Return (fc_before, fc_dropped, drop_ratio) or None if not applicable."""
    fc_before = mod_before.raw.get('function_count') if mod_before else None
    fc_after = mod_after.raw.get('function_count') if mod_after else None
    if fc_before is None or fc_after is None:
        return None
    if fc_before <= 1 or fc_after >= fc_before:
        return None
    fc_dropped = fc_before - fc_after
    drop_ratio = fc_dropped / fc_before
    if drop_ratio < 0.3:
        return None
    return (fc_before, fc_dropped, drop_ratio)

def _avg_func_length(funcs: dict[str, SymbolMetrics]) -> float | None:
    """Return average function length or None if no lengths available."""
    lengths = [ln for m in funcs.values() if (ln := _func_length(m)) is not None]
    return sum(lengths) / len(lengths) if lengths else None

def _largest_function(funcs: dict[str, SymbolMetrics]) -> tuple[str, SymbolMetrics, int] | None:
    """Return (name, metrics, length) of the largest function, or None."""
    candidates = [(sym, m) for sym, m in funcs.items() if _func_length(m) is not None]
    if not candidates:
        return None
    sym, m = max(candidates, key=lambda t: _func_length(t[1]) or 0)
    return (sym, m, _func_length(m) or 0)

def _check_god_function(file: str, funcs_before: dict[str, SymbolMetrics], funcs_after: dict[str, SymbolMetrics], mod_before: SymbolMetrics | None, mod_after: SymbolMetrics | None, config: RegressionConfig, ref_b: str, ref_a: str) -> list[ArchSmell]:
    """Detect when function count dropped and one function grew disproportionately."""
    drop = _function_count_drop(mod_before, mod_after)
    if drop is None:
        return []
    fc_before, fc_dropped, drop_ratio = drop
    fc_after = fc_before - fc_dropped
    avg_before = _avg_func_length(funcs_before)
    if avg_before is None:
        return []
    largest = _largest_function(funcs_after)
    if largest is None:
        return []
    largest_sym, largest_m, largest_len = largest
    if largest_len < config.god_func_length_min or largest_len <= avg_before * 1.5:
        return []
    severity = 'error' if largest_len > avg_before * 2.5 or fc_dropped >= 2 else 'warning'
    return [ArchSmell(smell='god_function', file=file, symbol=largest_sym, line=largest_m.line_start, severity=severity, detail=f"Function count dropped {fc_before}→{fc_after} ({drop_ratio:.0%}); '{largest_sym}' is {largest_len} lines (avg was {avg_before:.0f})", ref_before=ref_b, ref_after=ref_a)]

def _check_stub_regression(file: str, sym: str, m_before: SymbolMetrics, m_after: SymbolMetrics, config: RegressionConfig, ref_b: str, ref_a: str) -> ArchSmell | None:
    """Detect when a substantial function shrank to a near-empty stub."""
    len_b = _func_length(m_before)
    len_a = _func_length(m_after)
    calls_a = m_after.call_count
    if len_b is None or len_a is None or calls_a is None:
        return None
    if len_b <= config.stub_max_lines:
        return None
    if len_a > config.stub_max_lines:
        return None
    if len_a / len_b > config.stub_shrink_ratio:
        return None
    if calls_a > 0:
        return None
    severity = 'error' if len_a / len_b < 0.3 else 'warning'
    return ArchSmell(smell='stub_regression', file=file, symbol=sym, line=m_after.line_start, severity=severity, detail=f'Function shrank {len_b}→{len_a} lines ({len_a / len_b:.0%}) with no external calls', ref_before=ref_b, ref_after=ref_a)

def _check_no_delegation(file: str, sym: str, m_before: SymbolMetrics, m_after: SymbolMetrics, config: RegressionConfig, ref_b: str, ref_a: str) -> ArchSmell | None:
    """Detect when a function that previously delegated work now has no calls or params."""
    calls_a = m_after.call_count
    params_a = m_after.param_count
    calls_b = m_before.call_count
    params_b = m_before.param_count
    if calls_a is None or params_a is None:
        return None
    if calls_a > 0 or params_a > 0:
        return None
    len_a = _func_length(m_after)
    if len_a is not None and len_a > config.stub_max_lines * 2:
        return None
    had_calls = calls_b is not None and calls_b > 0
    had_params = params_b is not None and params_b > 0
    if not had_calls and (not had_params):
        return None
    was_before = []
    if had_calls:
        was_before.append(f'{calls_b} call(s)')
    if had_params:
        was_before.append(f'{params_b} param(s)')
    return ArchSmell(smell='no_delegation', file=file, symbol=sym, line=m_after.line_start, severity='warning', detail=f"'{sym}' lost all delegation: 0 params, 0 calls (before: {', '.join(was_before)})", ref_before=ref_b, ref_after=ref_a)

def _check_logic_density_drop(file: str, sym: str, m_before: SymbolMetrics, m_after: SymbolMetrics, config: RegressionConfig, ref_b: str, ref_a: str) -> ArchSmell | None:
    """Detect when statement density per line dropped below threshold."""
    ld_b = m_before.logic_density
    ld_a = m_after.logic_density
    if ld_b is None or ld_a is None:
        return None
    if ld_b < config.min_logic_density:
        return None
    if ld_a >= config.min_logic_density:
        return None
    drop = ld_b - ld_a
    severity = 'error' if drop > 0.3 else 'warning'
    return ArchSmell(smell='logic_density_drop', file=file, symbol=sym, line=m_after.line_start, severity=severity, detail=f'Logic density dropped {ld_b:.2f}→{ld_a:.2f} (min: {config.min_logic_density})', ref_before=ref_b, ref_after=ref_a)

def _check_cohesion_loss(file: str, sym: str, m_before: SymbolMetrics, m_after: SymbolMetrics, config: RegressionConfig, ref_b: str, ref_a: str) -> ArchSmell | None:
    """Detect when function body collapsed to a single statement type."""
    div_b = m_before.node_type_diversity
    div_a = m_after.node_type_diversity
    if div_b is None or div_a is None:
        return None
    if div_b < config.min_node_diversity:
        return None
    if div_a >= config.min_node_diversity:
        return None
    return ArchSmell(smell='cohesion_loss', file=file, symbol=sym, line=m_after.line_start, severity='warning', detail=f'Node type diversity dropped {div_b}→{div_a} unique statement types (min: {config.min_node_diversity})', ref_before=ref_b, ref_after=ref_a)

def _count_hollow_signals(m: SymbolMetrics, config: RegressionConfig) -> int:
    """Count how many hollow-code indicators a symbol exhibits."""
    signals = 0
    length = _func_length(m)
    if length is not None and length <= config.hallucination_max_lines:
        signals += 1
    if m.logic_density is not None and m.logic_density < config.min_logic_density:
        signals += 1
    if m.cc is not None and m.cc <= 1:
        signals += 1
    return signals

def _was_already_hollow(m_before: SymbolMetrics, config: RegressionConfig) -> bool:
    """Return True if the function was already hollow before the change."""
    calls_b = m_before.call_count
    ld_b = m_before.logic_density
    len_b = _func_length(m_before)
    return (calls_b is None or calls_b == 0) and (ld_b is None or ld_b < config.min_logic_density) and (len_b is None or len_b <= config.hallucination_max_lines)

def _check_hallucination_proxy(file: str, sym: str, m_before: SymbolMetrics | None, m_after: SymbolMetrics, config: RegressionConfig, ref_b: str, ref_a: str) -> ArchSmell | None:
    """Detect hollow/stub functions: zero calls + very low density + trivial CC.

    Only fires as a regression when the function was not already hollow before.
    """
    if m_after.call_count is None or m_after.logic_density is None:
        return None
    if m_after.call_count > 0:
        return None
    if _count_hollow_signals(m_after, config) < 2:
        return None
    if m_before is not None and _was_already_hollow(m_before, config):
        return None
    len_a = _func_length(m_after)
    return ArchSmell(smell='hallucination_proxy', file=file, symbol=sym, line=m_after.line_start, severity='warning', detail=f"'{sym}': calls=0, density={m_after.logic_density:.2f}, length={len_a or '?'}, cc={m_after.cc or '?'} — appears hollow (stub or placeholder)", ref_before=ref_b, ref_after=ref_a)