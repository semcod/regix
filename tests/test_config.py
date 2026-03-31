"""Tests for regix.config."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from regix.config import RegressionConfig


class TestRegressionConfig:
    def test_defaults(self):
        cfg = RegressionConfig()
        assert cfg.cc_max == 15.0
        assert cfg.mi_min == 20.0
        assert cfg.coverage_min == 80.0
        assert cfg.delta_warn == 2.0
        assert cfg.delta_error == 5.0
        assert cfg.on_regression == "warn"

    def test_from_dict_flat(self):
        data = {
            "regix": {
                "workdir": "/tmp/test",
                "metrics": {"cc_max": 10, "mi_min": 30},
                "thresholds": {"delta_warn": 1, "delta_error": 3},
            }
        }
        cfg = RegressionConfig.from_dict(data)
        assert cfg.cc_max == 10.0
        assert cfg.mi_min == 30.0
        assert cfg.delta_warn == 1.0
        assert cfg.delta_error == 3.0

    def test_from_yaml_file(self, tmp_path: Path):
        yaml_content = """\
regix:
  workdir: .
  metrics:
    cc_max: 12
    coverage_min: 90
  thresholds:
    delta_warn: 3
  backends:
    cc: radon
  exclude:
    - "tests/**"
  output:
    format: json
"""
        cfg_file = tmp_path / "regix.yaml"
        cfg_file.write_text(yaml_content)
        cfg = RegressionConfig.from_file(cfg_file)
        assert cfg.cc_max == 12.0
        assert cfg.coverage_min == 90.0
        assert cfg.delta_warn == 3.0
        assert cfg.output_format == "json"
        assert "tests/**" in cfg.exclude

    def test_from_file_directory_search(self, tmp_path: Path):
        yaml_content = "regix:\n  metrics:\n    cc_max: 8\n"
        (tmp_path / "regix.yaml").write_text(yaml_content)
        cfg = RegressionConfig.from_file(tmp_path)
        assert cfg.cc_max == 8.0

    def test_from_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            RegressionConfig.from_file(tmp_path / "nonexistent")

    def test_delta_thresholds_default(self):
        cfg = RegressionConfig(delta_warn=2.0, delta_error=5.0)
        warn, error = cfg.delta_thresholds("cc")
        assert warn == 2.0
        assert error == 5.0

    def test_delta_thresholds_per_metric(self):
        cfg = RegressionConfig(
            delta_warn=2.0, delta_error=5.0,
            per_metric={"coverage": {"delta_warn": 1, "delta_error": 3}},
        )
        warn, error = cfg.delta_thresholds("coverage")
        assert warn == 1.0
        assert error == 3.0
        # Fallback for unspecified metric
        warn2, error2 = cfg.delta_thresholds("cc")
        assert warn2 == 2.0

    def test_is_lower_better(self):
        cfg = RegressionConfig()
        assert cfg.is_lower_better("cc") is True
        assert cfg.is_lower_better("length") is True
        assert cfg.is_lower_better("mi") is False
        assert cfg.is_lower_better("coverage") is False

    def test_env_overrides(self, monkeypatch):
        cfg = RegressionConfig()
        monkeypatch.setenv("REGIX_CC_MAX", "25")
        monkeypatch.setenv("REGIX_FORMAT", "json")
        cfg.apply_env_overrides()
        assert cfg.cc_max == 25.0
        assert cfg.output_format == "json"
