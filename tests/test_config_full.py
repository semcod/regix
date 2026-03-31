"""Tests for regix.config — from_dict, from_file, aliases, env overrides."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from regix.config import (
    DEFAULT_CC_HARD,
    DEFAULT_CC_TARGET,
    DEFAULT_COVERAGE_HARD,
    DEFAULT_MI_HARD,
    GateThresholds,
    RegressionConfig,
)


class TestGateThresholdsGet:
    def test_get_known(self):
        gt = GateThresholds(cc=10.0)
        assert gt.get("cc") == 10.0

    def test_get_unknown_raises(self):
        gt = GateThresholds()
        with pytest.raises(AttributeError):
            gt.get("nonexistent")


class TestRegressionConfigAliases:
    def test_cc_max_getter(self):
        cfg = RegressionConfig()
        assert cfg.cc_max == DEFAULT_CC_HARD

    def test_cc_max_setter(self):
        cfg = RegressionConfig()
        cfg.cc_max = 99.0
        assert cfg.hard.cc == 99.0

    def test_mi_min(self):
        cfg = RegressionConfig()
        assert cfg.mi_min == DEFAULT_MI_HARD
        cfg.mi_min = 25.0
        assert cfg.hard.mi == 25.0

    def test_coverage_min(self):
        cfg = RegressionConfig()
        assert cfg.coverage_min == DEFAULT_COVERAGE_HARD
        cfg.coverage_min = 70.0
        assert cfg.hard.coverage == 70.0

    def test_length_max(self):
        cfg = RegressionConfig()
        cfg.length_max = 200.0
        assert cfg.hard.length == 200.0

    def test_docstring_min(self):
        cfg = RegressionConfig()
        cfg.docstring_min = 50.0
        assert cfg.hard.docstring == 50.0

    def test_quality_min(self):
        cfg = RegressionConfig()
        cfg.quality_min = 0.9
        assert cfg.hard.quality == 0.9

    def test_target_properties(self):
        cfg = RegressionConfig()
        assert cfg.cc_target == DEFAULT_CC_TARGET
        assert cfg.mi_target > 0
        assert cfg.coverage_target > 0
        assert cfg.length_target > 0
        assert cfg.docstring_target > 0
        assert cfg.quality_target > 0


class TestFromDict:
    def test_new_format_gates(self):
        data = {
            "gates": {
                "hard": {"cc": 20.0, "mi": 10.0},
                "target": {"cc": 8.0},
            }
        }
        cfg = RegressionConfig.from_dict(data)
        assert cfg.hard.cc == 20.0
        assert cfg.target.cc == 8.0

    def test_legacy_metrics(self):
        data = {
            "metrics": {"cc_max": 25.0, "mi_min": 15.0, "coverage_target": 90.0}
        }
        cfg = RegressionConfig.from_dict(data)
        assert cfg.hard.cc == 25.0
        assert cfg.hard.mi == 15.0
        assert cfg.target.coverage == 90.0

    def test_deltas_new_format(self):
        data = {"deltas": {"warn": 3.0, "error": 8.0}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.delta_warn == 3.0
        assert cfg.delta_error == 8.0

    def test_legacy_thresholds(self):
        data = {"thresholds": {"delta_warn": 2.5, "delta_error": 7.0}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.delta_warn == 2.5
        assert cfg.delta_error == 7.0

    def test_smells_config(self):
        data = {"smells": {"stub_max_lines": 5, "min_logic_density": 0.3}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.stub_max_lines == 5
        assert cfg.min_logic_density == 0.3

    def test_exclude_include(self):
        data = {"exclude": ["tests/**"], "include": ["src/**"]}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.exclude == ["tests/**"]
        assert cfg.include == ["src/**"]

    def test_backends_config(self):
        data = {"backends": {"cc": "lizard", "mi": "radon", "parallel": True}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.backends["cc"] == "lizard"
        assert cfg.backends_parallel is True

    def test_output_config(self):
        data = {"output": {"format": "json", "dir": ".out", "show_improvements": True, "max_symbols": 50}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.output_format == "json"
        assert cfg.output_dir == ".out"

    def test_cache_config(self):
        data = {"cache": {"enabled": False, "dir": "/tmp/cache"}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.cache_enabled is False
        assert cfg.cache_dir == "/tmp/cache"

    def test_loop_config(self):
        data = {"loop": {"stagnation_window": 5}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.stagnation_window == 5

    def test_on_regression_and_exit_code(self):
        data = {"gates": {"on_regression": "warn", "fail_exit_code": 2}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.on_regression == "warn"
        assert cfg.fail_exit_code == 2

    def test_regix_key_unwrapping(self):
        data = {"regix": {"deltas": {"warn": 1.0}}}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.delta_warn == 1.0

    def test_workdir(self):
        data = {"workdir": "/tmp/proj"}
        cfg = RegressionConfig.from_dict(data)
        assert cfg.workdir == "/tmp/proj"


class TestFromFile:
    def test_yaml_file(self, tmp_path: Path):
        cfg_data = {"gates": {"hard": {"cc": 20.0}}}
        p = tmp_path / "regix.yaml"
        p.write_text(yaml.dump(cfg_data))
        cfg = RegressionConfig.from_file(p)
        assert cfg.hard.cc == 20.0

    def test_directory_finds_yaml(self, tmp_path: Path):
        cfg_data = {"gates": {"hard": {"cc": 25.0}}}
        p = tmp_path / "regix.yaml"
        p.write_text(yaml.dump(cfg_data))
        cfg = RegressionConfig.from_file(tmp_path)
        assert cfg.hard.cc == 25.0

    def test_directory_no_config_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            RegressionConfig.from_file(tmp_path)

    def test_pyproject_toml(self, tmp_path: Path):
        p = tmp_path / "pyproject.toml"
        p.write_text('[tool.regix.gates.hard]\ncc = 18.0\n')
        cfg = RegressionConfig.from_file(p)
        assert cfg.hard.cc == 18.0

    def test_pyproject_no_regix_section(self, tmp_path: Path):
        p = tmp_path / "pyproject.toml"
        p.write_text('[tool.other]\nfoo = 1\n')
        cfg = RegressionConfig.from_file(p)
        assert cfg.hard.cc == DEFAULT_CC_HARD  # defaults


class TestDeltaThresholds:
    def test_default_thresholds(self):
        cfg = RegressionConfig()
        warn, error = cfg.delta_thresholds("cc")
        assert warn > 0
        assert error > warn

    def test_per_metric_override(self):
        cfg = RegressionConfig(per_metric={"cc": {"delta_warn": 1.0, "delta_error": 3.0}})
        warn, error = cfg.delta_thresholds("cc")
        assert warn == 1.0
        assert error == 3.0

    def test_unknown_metric_uses_defaults(self):
        cfg = RegressionConfig()
        warn, error = cfg.delta_thresholds("unknown_metric")
        assert warn == cfg.delta_warn
        assert error == cfg.delta_error


class TestIsLowerBetter:
    def test_cc_lower_is_better(self):
        cfg = RegressionConfig()
        assert cfg.is_lower_better("cc") is True

    def test_mi_higher_is_better(self):
        cfg = RegressionConfig()
        assert cfg.is_lower_better("mi") is False

    def test_coverage_higher_is_better(self):
        cfg = RegressionConfig()
        assert cfg.is_lower_better("coverage") is False


class TestEnvOverrides:
    def test_env_override_cc_max(self, monkeypatch):
        monkeypatch.setenv("REGIX_CC_MAX", "42")
        cfg = RegressionConfig()
        cfg.apply_env_overrides()
        assert cfg.cc_max == 42.0

    def test_env_override_workdir(self, monkeypatch):
        monkeypatch.setenv("REGIX_WORKDIR", "/custom/path")
        cfg = RegressionConfig()
        cfg.apply_env_overrides()
        assert cfg.workdir == "/custom/path"

    def test_env_override_cache_enabled(self, monkeypatch):
        monkeypatch.setenv("REGIX_CACHE_ENABLED", "true")
        cfg = RegressionConfig()
        cfg.apply_env_overrides()
        assert cfg.cache_enabled is True

    def test_no_env_no_change(self):
        cfg = RegressionConfig()
        original_cc = cfg.cc_max
        cfg.apply_env_overrides()
        assert cfg.cc_max == original_cc
