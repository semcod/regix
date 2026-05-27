"""Tests for regix.impact."""

from __future__ import annotations

from regix.config import RegressionConfig
from regix.impact import ImpactAnalyzer


def test_import_graph_adds_transitive_test_targets(tmp_path):
    app_dir = tmp_path / "app"
    tests_dir = tmp_path / "tests"
    app_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    (app_dir / "core.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (app_dir / "service.py").write_text(
        "from app.core import value\n\ndef run():\n    return value()\n",
        encoding="utf-8",
    )
    (tests_dir / "test_service.py").write_text(
        "from app.service import run\n\ndef test_run():\n    assert run() == 1\n",
        encoding="utf-8",
    )

    cfg = RegressionConfig(
        impact_include_prefixes=[],
        impact_ignore_globs=[],
        impact_test_patterns=[],
        impact_enable_import_graph=True,
        impact_transitive_depth=3,
    )
    analyzer = ImpactAnalyzer(str(tmp_path), cfg)

    analysis = analyzer.analyze_impact(["app/core.py"])

    assert "tests/test_service.py" in analysis["pytest_targets"]
    assert "app.core" in analysis["impacted_modules"]
    assert "app.service" in analysis["transitive_dependents"]


def test_import_graph_can_be_disabled(tmp_path):
    app_dir = tmp_path / "app"
    tests_dir = tmp_path / "tests"
    app_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    (app_dir / "core.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (tests_dir / "test_core.py").write_text(
        "from app.core import value\n\ndef test_value():\n    assert value() == 1\n",
        encoding="utf-8",
    )

    cfg = RegressionConfig(
        impact_include_prefixes=[],
        impact_ignore_globs=[],
        impact_test_patterns=[],
        impact_enable_import_graph=False,
    )
    analyzer = ImpactAnalyzer(str(tmp_path), cfg)

    analysis = analyzer.analyze_impact(["app/core.py"])

    assert analysis["impacted_modules"] == []
    assert analysis["transitive_dependents"] == []
