"""Configuration for Regix — thresholds, backends, file patterns."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Default gate threshold constants ─────────────────────────────────────────
DEFAULT_CC_HARD = 15.0
DEFAULT_MI_HARD = 20.0
DEFAULT_COVERAGE_HARD = 80.0
DEFAULT_LENGTH_HARD = 100.0
DEFAULT_DOCSTRING_HARD = 60.0
DEFAULT_QUALITY_HARD = 0.85

DEFAULT_CC_TARGET = 10.0
DEFAULT_MI_TARGET = 30.0
DEFAULT_COVERAGE_TARGET = 90.0
DEFAULT_LENGTH_TARGET = 50.0
DEFAULT_DOCSTRING_TARGET = 80.0
DEFAULT_QUALITY_TARGET = 0.95


# ── Metric direction: True means "lower is better" ──────────────────────────
METRIC_DIRECTIONS: dict[str, bool] = {
    "cc": True,          # lower CC is better → positive delta = regression
    "length": True,
    "imports": True,
    "mi": False,         # higher MI is better → negative delta = regression
    "coverage": False,
    "docstring_coverage": False,
    "quality_score": False,
    "fan_out": False,            # more delegation = better → drop = regression
    "call_count": False,          # more calls = less shell → drop = regression
    "symbol_count": False,        # more symbols = better structure → drop = regression
    "logic_density": False,       # higher density is better → drop = regression
    "node_type_diversity": False, # more diversity is better → drop = regression
}

# ── Per-metric delta thresholds: (warn, error) ───────────────────────────────
METRIC_THRESHOLDS: dict[str, tuple[float, float]] = {
    "symbol_count": (1.0, 3.0),   # losing 1 function = warn, 3 = error
    "fan_out": (2.0, 5.0),        # losing 2 unique calls = warn, 5 = error
    "call_count": (3.0, 7.0),          # losing 3 total calls = warn, 7 = error
    "logic_density": (0.10, 0.20),      # drop of 0.10 = warn, 0.20 = error
    "node_type_diversity": (1.0, 2.0),  # losing 1 type = warn, 2 = error
}

# ── Metric names used by gates (bare name → model attr, operator) ────────────
GATE_METRICS: list[tuple[str, str, str]] = [
    # (gate_key, SymbolMetrics attr, operator)
    ("cc", "cc", "le"),
    ("mi", "mi", "ge"),
    ("coverage", "coverage", "ge"),
    ("length", "length", "le"),
    ("docstring", "docstring_coverage", "ge"),
    ("quality", "quality_score", "ge"),
]


@dataclass
class GateThresholds:
    """Threshold set for a single tier (hard or target).

    Keys use **bare metric names** (``cc``, ``mi``, ``coverage``, …).
    The direction (``≤`` or ``≥``) is defined by :data:`METRIC_DIRECTIONS`
    and :data:`GATE_METRICS`.
    """

    cc: float = DEFAULT_CC_HARD
    mi: float = DEFAULT_MI_HARD
    coverage: float = DEFAULT_COVERAGE_HARD
    length: float = DEFAULT_LENGTH_HARD
    docstring: float = DEFAULT_DOCSTRING_HARD
    quality: float = DEFAULT_QUALITY_HARD

    def get(self, key: str) -> float:
        """Look up a threshold by bare metric name."""
        return getattr(self, key)


# ── Default tiers ────────────────────────────────────────────────────────────
_HARD_DEFAULTS = GateThresholds(
    cc=DEFAULT_CC_HARD, mi=DEFAULT_MI_HARD, coverage=DEFAULT_COVERAGE_HARD,
    length=DEFAULT_LENGTH_HARD, docstring=DEFAULT_DOCSTRING_HARD, quality=DEFAULT_QUALITY_HARD,
)
_TARGET_DEFAULTS = GateThresholds(
    cc=DEFAULT_CC_TARGET, mi=DEFAULT_MI_TARGET, coverage=DEFAULT_COVERAGE_TARGET,
    length=DEFAULT_LENGTH_TARGET, docstring=DEFAULT_DOCSTRING_TARGET, quality=DEFAULT_QUALITY_TARGET,
)


@dataclass
class RegressionConfig:
    """All user-configurable values for a Regix run."""

    # ── Gate thresholds ───────────────────────────────────────────────────────
    hard: GateThresholds = field(default_factory=lambda: GateThresholds(
        cc=DEFAULT_CC_HARD, mi=DEFAULT_MI_HARD, coverage=DEFAULT_COVERAGE_HARD,
        length=DEFAULT_LENGTH_HARD, docstring=DEFAULT_DOCSTRING_HARD, quality=DEFAULT_QUALITY_HARD,
    ))
    target: GateThresholds = field(default_factory=lambda: GateThresholds(
        cc=DEFAULT_CC_TARGET, mi=DEFAULT_MI_TARGET, coverage=DEFAULT_COVERAGE_TARGET,
        length=DEFAULT_LENGTH_TARGET, docstring=DEFAULT_DOCSTRING_TARGET, quality=DEFAULT_QUALITY_TARGET,
    ))

    # ── Delta thresholds (relative change between commits) ────────────────────
    delta_warn: float = 2.0
    delta_error: float = 5.0
    per_metric: dict[str, dict[str, float]] = field(default_factory=dict)

    # ── File filtering ────────────────────────────────────────────────────────
    exclude: list[str] = field(default_factory=lambda: [
        "tests/**", "docs/**", "examples/**", ".venv/**", "venv/**",
        "build/**", "dist/**", "**/migrations/**", "**/*_pb2.py",
    ])
    include: list[str] = field(default_factory=list)

    # ── Backends ──────────────────────────────────────────────────────────────
    backends: dict[str, str] = field(default_factory=lambda: {
        "cc": "lizard", "mi": "radon", "coverage": "pytest-cov",
        "quality": "vallm", "docstring": "builtin",
    })
    backends_parallel: bool = False

    # ── Pipeline behaviour ────────────────────────────────────────────────────
    on_regression: str = "warn"
    fail_exit_code: int = 1

    # ── Output ────────────────────────────────────────────────────────────────
    show_improvements: bool = True
    output_format: str = "rich"
    output_dir: str = ".regix/"
    max_symbols: int = 100

    # ── Cache ─────────────────────────────────────────────────────────────────
    cache_enabled: bool = True
    cache_dir: str = "~/.cache/regix"

    # ── Misc ──────────────────────────────────────────────────────────────────
    stagnation_window: int = 2
    workdir: str | Path = "."
    metric_directions: dict[str, bool] = field(
        default_factory=lambda: dict(METRIC_DIRECTIONS)
    )

    # ── Architectural smell thresholds ────────────────────────────────────────
    stub_max_lines: int = 5
    stub_shrink_ratio: float = 0.50
    min_logic_density: float = 0.20
    min_node_diversity: int = 2
    god_func_length_min: int = 30
    hallucination_max_lines: int = 6

    # ── Backward-compatible aliases ───────────────────────────────────────────
    # Code that reads cfg.cc_max still works.

    @property
    def cc_max(self) -> float:
        return self.hard.cc

    @cc_max.setter
    def cc_max(self, v: float) -> None:
        self.hard.cc = v

    @property
    def mi_min(self) -> float:
        return self.hard.mi

    @mi_min.setter
    def mi_min(self, v: float) -> None:
        self.hard.mi = v

    @property
    def coverage_min(self) -> float:
        return self.hard.coverage

    @coverage_min.setter
    def coverage_min(self, v: float) -> None:
        self.hard.coverage = v

    @property
    def length_max(self) -> float:
        return self.hard.length

    @length_max.setter
    def length_max(self, v: float) -> None:
        self.hard.length = v

    @property
    def docstring_min(self) -> float:
        return self.hard.docstring

    @docstring_min.setter
    def docstring_min(self, v: float) -> None:
        self.hard.docstring = v

    @property
    def quality_min(self) -> float:
        return self.hard.quality

    @quality_min.setter
    def quality_min(self, v: float) -> None:
        self.hard.quality = v

    @property
    def cc_target(self) -> float:
        return self.target.cc

    @property
    def mi_target(self) -> float:
        return self.target.mi

    @property
    def coverage_target(self) -> float:
        return self.target.coverage

    @property
    def length_target(self) -> float:
        return self.target.length

    @property
    def docstring_target(self) -> float:
        return self.target.docstring

    @property
    def quality_target(self) -> float:
        return self.target.quality

    # ── Loaders ──────────────────────────────────────────────────────────────

    @classmethod
    def from_file(cls, path: str | Path) -> RegressionConfig:
        """Load config from YAML or pyproject.toml."""
        p = Path(path)
        if p.is_dir():
            p = cls._find_config(p)
        if p.suffix == ".toml":
            return cls._from_pyproject(p)
        return cls._from_yaml(p)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegressionConfig:
        """Build config from a flat or nested dict.

        Supports two config layouts:

        **New (recommended)**::

            gates:
              hard:  {cc: 30, mi: 15, ...}
              target: {cc: 10, mi: 30, ...}
            deltas: {warn: 2, error: 5}

        **Legacy**::

            metrics: {cc_max: 30, mi_min: 15, cc_target: 10, ...}
            thresholds: {delta_warn: 2, delta_error: 5}
        """
        root = data.get("regix", data)
        kwargs: dict[str, Any] = {}

        if "workdir" in root:
            kwargs["workdir"] = root["workdir"]

        # ── Gates (new nested format) ────────────────────────────────────
        gates_cfg = root.get("gates", {})
        if "hard" in gates_cfg and isinstance(gates_cfg["hard"], dict):
            kwargs["hard"] = GateThresholds(**{
                k: float(v) for k, v in gates_cfg["hard"].items()
                if hasattr(GateThresholds, k)
            })
        if "target" in gates_cfg and isinstance(gates_cfg["target"], dict):
            kwargs["target"] = GateThresholds(**{
                k: float(v) for k, v in gates_cfg["target"].items()
                if hasattr(GateThresholds, k)
            })
        if "on_regression" in gates_cfg:
            kwargs["on_regression"] = gates_cfg["on_regression"]
        if "fail_exit_code" in gates_cfg:
            kwargs["fail_exit_code"] = int(gates_cfg["fail_exit_code"])

        # ── Legacy flat metrics ──────────────────────────────────────────
        metrics = root.get("metrics", {})
        if metrics:
            _LEGACY_HARD = {"cc_max": "cc", "mi_min": "mi", "coverage_min": "coverage",
                            "length_max": "length", "docstring_min": "docstring",
                            "quality_min": "quality"}
            _LEGACY_TARGET = {"cc_target": "cc", "mi_target": "mi",
                              "coverage_target": "coverage", "length_target": "length",
                              "docstring_target": "docstring", "quality_target": "quality"}
            if "hard" not in kwargs:
                hard_vals = {}
                for old_key, new_key in _LEGACY_HARD.items():
                    if old_key in metrics:
                        hard_vals[new_key] = float(metrics[old_key])
                if hard_vals:
                    kwargs["hard"] = GateThresholds(**hard_vals)
            if "target" not in kwargs:
                tgt_vals = {}
                for old_key, new_key in _LEGACY_TARGET.items():
                    if old_key in metrics:
                        tgt_vals[new_key] = float(metrics[old_key])
                if tgt_vals:
                    kwargs["target"] = GateThresholds(**tgt_vals)

        # ── Deltas (new format) ──────────────────────────────────────────
        deltas = root.get("deltas", {})
        if "warn" in deltas:
            kwargs["delta_warn"] = float(deltas["warn"])
        if "error" in deltas:
            kwargs["delta_error"] = float(deltas["error"])

        # ── Legacy thresholds ────────────────────────────────────────────
        thresholds = root.get("thresholds", {})
        if "delta_warn" in thresholds:
            kwargs.setdefault("delta_warn", float(thresholds["delta_warn"]))
        if "delta_error" in thresholds:
            kwargs.setdefault("delta_error", float(thresholds["delta_error"]))
        if "per_metric" in thresholds:
            kwargs["per_metric"] = thresholds["per_metric"]

        # ── Smells ───────────────────────────────────────────────────────
        smells_cfg = root.get("smells", {})
        for key in ("stub_max_lines", "min_node_diversity", "god_func_length_min",
                    "hallucination_max_lines"):
            if key in smells_cfg:
                kwargs[key] = int(smells_cfg[key])
        for key in ("stub_shrink_ratio", "min_logic_density"):
            if key in smells_cfg:
                kwargs[key] = float(smells_cfg[key])

        # ── Files ────────────────────────────────────────────────────────
        if "exclude" in root:
            kwargs["exclude"] = root["exclude"]
        if "include" in root:
            kwargs["include"] = root["include"]

        # ── Backends ─────────────────────────────────────────────────────
        if "backends" in root:
            bk = root["backends"]
            if isinstance(bk, dict):
                kwargs["backends"] = {
                    k: v for k, v in bk.items() if k != "parallel"
                }
                if "parallel" in bk:
                    kwargs["backends_parallel"] = bk["parallel"]

        # ── Output ───────────────────────────────────────────────────────
        output = root.get("output", {})
        if "format" in output:
            kwargs["output_format"] = output["format"]
        if "dir" in output:
            kwargs["output_dir"] = output["dir"]
        if "show_improvements" in output:
            kwargs["show_improvements"] = output["show_improvements"]
        if "max_symbols" in output:
            kwargs["max_symbols"] = output["max_symbols"]

        # ── Cache ────────────────────────────────────────────────────────
        cache = root.get("cache", {})
        if "enabled" in cache:
            kwargs["cache_enabled"] = cache["enabled"]
        if "dir" in cache:
            kwargs["cache_dir"] = cache["dir"]

        # ── Loop ─────────────────────────────────────────────────────────
        loop = root.get("loop", {})
        if "stagnation_window" in loop:
            kwargs["stagnation_window"] = int(loop["stagnation_window"])

        return cls(**kwargs)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def delta_thresholds(self, metric: str) -> tuple[float, float]:
        """Return (warn, error) thresholds for a specific metric."""
        pm = self.per_metric.get(metric, {})
        default_warn, default_error = METRIC_THRESHOLDS.get(
            metric, (self.delta_warn, self.delta_error)
        )
        warn = pm.get("delta_warn", default_warn)
        error = pm.get("delta_error", default_error)
        return warn, error

    def is_lower_better(self, metric: str) -> bool:
        return self.metric_directions.get(metric, True)

    # ── Private ──────────────────────────────────────────────────────────────

    @classmethod
    def _find_config(cls, directory: Path) -> Path:
        candidates = [
            directory / "regix.yaml",
            directory / ".regix" / "config.yaml",
            directory / "pyproject.toml",
        ]
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError(
            f"No regix config found in {directory}. "
            "Create regix.yaml, .regix/config.yaml, or add [tool.regix] to pyproject.toml."
        )

    @classmethod
    def _from_yaml(cls, path: Path) -> RegressionConfig:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.from_dict(data)

    @classmethod
    def _from_pyproject(cls, path: Path) -> RegressionConfig:
        try:
            import tomllib  # Python 3.11+
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ModuleNotFoundError:
                # Fallback: parse [tool.regix] manually via yaml-like approach
                with open(path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                # Minimal fallback — return defaults
                return cls()
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        tool_regix = data.get("tool", {}).get("regix", {})
        if not tool_regix:
            return cls()
        return cls.from_dict({"regix": tool_regix})

    def apply_env_overrides(self) -> None:
        """Override config values from REGIX_* environment variables."""
        env_map = {
            "REGIX_WORKDIR": ("workdir", str),
            "REGIX_CC_MAX": ("cc_max", float),
            "REGIX_MI_MIN": ("mi_min", float),
            "REGIX_COVERAGE_MIN": ("coverage_min", float),
            "REGIX_DELTA_WARN": ("delta_warn", float),
            "REGIX_DELTA_ERROR": ("delta_error", float),
            "REGIX_FORMAT": ("output_format", str),
            "REGIX_OUTPUT_DIR": ("output_dir", str),
            "REGIX_CACHE_ENABLED": ("cache_enabled", lambda v: v.lower() in ("1", "true", "yes")),
            "REGIX_CACHE_DIR": ("cache_dir", str),
            "REGIX_ON_REGRESSION": ("on_regression", str),
            "REGIX_FAIL_EXIT_CODE": ("fail_exit_code", int),
        }
        for env_key, (attr, converter) in env_map.items():
            val = os.environ.get(env_key)
            if val is not None:
                setattr(self, attr, converter(val))
