"""Per-function MI granularity for the radon backend (regix STARTER-026).

Module-level MI punishes total LOC, so extracting a helper to lower CC can push
module MI *down* below the gate even though the code got more maintainable.
``mi_granularity: function`` evaluates each unit's own span instead, so good
refactors stop being penalized.
"""

from pathlib import Path

import pytest

from regix.backends.radon_backend import RadonBackend
from regix.config import RegressionConfig

radon = pytest.importorskip("radon", reason="radon backend requires radon")


# A single high-CC function vs. the same logic split into small helpers.
_MONOLITH = '''
def classify(x):
    if x == 1:
        return "a"
    elif x == 2:
        return "b"
    elif x == 3:
        return "c"
    elif x == 4:
        return "d"
    elif x == 5:
        return "e"
    elif x == 6:
        return "f"
    else:
        return "z"
'''

_EXTRACTED = '''
_TABLE = {1: "a", 2: "b", 3: "c", 4: "d", 5: "e", 6: "f"}


def _lookup(x):
    return _TABLE.get(x)


def classify(x):
    hit = _lookup(x)
    return hit if hit is not None else "z"
'''


def _collect(source: str, tmp_path: Path, granularity: str):
    cfg = RegressionConfig(mi_granularity=granularity)
    f = tmp_path / "m.py"
    f.write_text(source)
    return RadonBackend().collect(tmp_path, [Path("m.py")], cfg, sources={"m.py": source})


def _module_mi(metrics):
    return next(m.mi for m in metrics if m.symbol is None)


def _function_mis(metrics):
    return {m.symbol: m.mi for m in metrics if m.symbol is not None}


def test_module_granularity_leaves_functions_without_mi(tmp_path):
    metrics = _collect(_MONOLITH, tmp_path, "module")
    assert _module_mi(metrics) is not None
    # Default behaviour unchanged: functions carry CC, not MI.
    assert all(v is None for v in _function_mis(metrics).values())


def test_function_granularity_emits_per_function_mi(tmp_path):
    metrics = _collect(_MONOLITH, tmp_path, "function")
    fmis = _function_mis(metrics)
    assert fmis.get("classify") is not None
    assert 0.0 <= fmis["classify"] <= 100.0
    # Module-level MI still present alongside per-function MI.
    assert _module_mi(metrics) is not None


def test_extraction_does_not_regress_per_function_mi(tmp_path):
    """The field case: extraction lowers CC; per-function MI must not punish it."""
    from radon.complexity import cc_visit

    mono = _collect(_MONOLITH, tmp_path, "function")
    extr = _collect(_EXTRACTED, tmp_path, "function")

    # Sanity: extraction really did cut the peak CC of `classify`.
    mono_cc = max(b.complexity for b in cc_visit(_MONOLITH))
    extr_classify_cc = next(
        m.cc for m in extr if m.symbol == "classify"
    )
    assert extr_classify_cc < mono_cc

    # The refactored `classify` scores at least as maintainable per-function as
    # the monolith did — the metric no longer fights the extraction.
    mono_classify_mi = next(m.mi for m in mono if m.symbol == "classify")
    extr_classify_mi = next(m.mi for m in extr if m.symbol == "classify")
    assert extr_classify_mi >= mono_classify_mi
