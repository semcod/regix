"""Configuration for Regix — thresholds, backends, file patterns."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


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


@dataclass
class RegressionConfig:
    """All user-configurable values for a Regix run."""

    cc_max: float = 15.0
    mi_min: float = 20.0
    coverage_min: float = 80.0
    length_max: int = 100
    docstring_min: float = 60.0
    quality_min: float = 0.85
    delta_warn: float = 2.0
    delta_error: float = 5.0
    per_metric: dict[str, dict[str, float]] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=lambda: [
        "tests/**", "docs/**", "examples/**", ".venv/**", "venv/**",
        "build/**", "dist/**", "**/migrations/**", "**/*_pb2.py",
    ])
    include: list[str] = field(default_factory=list)
    backends: dict[str, str] = field(default_factory=lambda: {
        "cc": "lizard", "mi": "radon", "coverage": "pytest-cov",
        "quality": "vallm", "docstring": "builtin",
    })
    backends_parallel: bool = False
    on_regression: str = "warn"
    fail_exit_code: int = 1
    show_improvements: bool = True
    output_format: str = "rich"
    output_dir: str = ".regix/"
    max_symbols: int = 100
    cache_enabled: bool = True
    cache_dir: str = "~/.cache/regix"
    stagnation_window: int = 2
    workdir: str | Path = "."
    metric_directions: dict[str, bool] = field(
        default_factory=lambda: dict(METRIC_DIRECTIONS)
    )
    # ── Architectural smell thresholds ───────────────────────────────────────
    stub_max_lines: int = 5             # max lines to qualify as a stub
    stub_shrink_ratio: float = 0.50     # function shrank to <50% → stub candidate
    min_logic_density: float = 0.20     # statements/lines below this = sparse
    min_node_diversity: int = 2         # unique stmt types below this = homogeneous
    god_func_length_min: int = 30       # minimum lines to be a god-function candidate
    hallucination_max_lines: int = 6    # max lines for hallucination proxy signal

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
        """Build config from a flat or nested dict."""
        root = data.get("regix", data)
        kwargs: dict[str, Any] = {}
        if "workdir" in root:
            kwargs["workdir"] = root["workdir"]
        metrics = root.get("metrics", {})
        for key in ("cc_max", "mi_min", "coverage_min", "length_max",
                     "docstring_min", "quality_min"):
            if key in metrics:
                kwargs[key] = float(metrics[key])
        thresholds = root.get("thresholds", {})
        for key in ("delta_warn", "delta_error"):
            if key in thresholds:
                kwargs[key] = float(thresholds[key])
        if "per_metric" in thresholds:
            kwargs["per_metric"] = thresholds["per_metric"]
        smells_cfg = root.get("smells", {})
        for key in ("stub_max_lines", "min_node_diversity", "god_func_length_min",
                    "hallucination_max_lines"):
            if key in smells_cfg:
                kwargs[key] = int(smells_cfg[key])
        for key in ("stub_shrink_ratio", "min_logic_density"):
            if key in smells_cfg:
                kwargs[key] = float(smells_cfg[key])
        if "exclude" in root:
            kwargs["exclude"] = root["exclude"]
        if "include" in root:
            kwargs["include"] = root["include"]
        if "backends" in root:
            bk = root["backends"]
            if isinstance(bk, dict):
                kwargs["backends"] = {
                    k: v for k, v in bk.items() if k != "parallel"
                }
                if "parallel" in bk:
                    kwargs["backends_parallel"] = bk["parallel"]
        output = root.get("output", {})
        if "format" in output:
            kwargs["output_format"] = output["format"]
        if "dir" in output:
            kwargs["output_dir"] = output["dir"]
        if "show_improvements" in output:
            kwargs["show_improvements"] = output["show_improvements"]
        if "max_symbols" in output:
            kwargs["max_symbols"] = output["max_symbols"]
        cache = root.get("cache", {})
        if "enabled" in cache:
            kwargs["cache_enabled"] = cache["enabled"]
        if "dir" in cache:
            kwargs["cache_dir"] = cache["dir"]
        gates = root.get("gates", {})
        if "on_regression" in gates:
            kwargs["on_regression"] = gates["on_regression"]
        if "fail_exit_code" in gates:
            kwargs["fail_exit_code"] = int(gates["fail_exit_code"])
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
