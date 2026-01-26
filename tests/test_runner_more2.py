from __future__ import annotations

from pathlib import Path

import pytest

from codegate.engine.runner import EvaluationRunner


def test_prepare_environment_raises_when_project_path_missing(tmp_path: Path):
    runner = EvaluationRunner(verbose=False)

    contract_env = {"runtime_image": "python:3.12-slim"}
    project = {"path": str(tmp_path / "nope"), "entry_point": "x"}

    with pytest.raises(ValueError):
        runner._prepare_environment(contract_env, project)


def test_prepare_environment_docker_unavailable_sets_no_deps_image(monkeypatch, tmp_path: Path):
    runner = EvaluationRunner(verbose=True)

    # Fake docker not available
    monkeypatch.setattr(runner.docker_runner, "is_available", lambda: False)

    artifact_info = runner._prepare_environment(
        {"runtime_image": "python:3.12-slim", "network_access": True},
        {"path": str(tmp_path), "entry_point": "main"},
    )

    assert artifact_info["deps_image"] is None
    assert artifact_info["network_access"] is True


def test_prepare_environment_docker_build_failure_falls_back(monkeypatch, tmp_path: Path):
    runner = EvaluationRunner(verbose=True)

    monkeypatch.setattr(runner.docker_runner, "is_available", lambda: True)

    def _build(*args, **kwargs):
        raise RuntimeError("build failed")

    monkeypatch.setattr(runner.docker_runner, "build_deps_image", _build)

    artifact_info = runner._prepare_environment(
        {"runtime_image": "python:3.12-slim", "network_access": False},
        {"path": str(tmp_path), "entry_point": "main"},
    )

    assert artifact_info["deps_image"] is None


def test_run_skips_disabled_rules_and_aggregates(monkeypatch, tmp_path: Path):
    runner = EvaluationRunner(verbose=False)

    # Avoid touching docker for this test
    monkeypatch.setattr(runner, "_prepare_environment", lambda env, proj: {"absolute_path": str(tmp_path)})

    called = {"n": 0}

    def _run_rule(rule_name, rule_config, artifact_info):
        called["n"] += 1
        from codegate.engine.result import RuleResult

        return RuleResult(rule_name=rule_name, passed=True, message="ok", details={}, duration=0.0)

    monkeypatch.setattr(runner, "_run_rule", _run_rule)

    contract = {
        "Environment": {},
        "project": {"path": str(tmp_path), "entry_point": "ep"},
        "rules": {
            "unit_tests": {"enabled": False},
            "policy": {},
        },
    }

    result = runner.run(contract)

    assert called["n"] == 1
    assert result["summary"]["total"] == 1
    assert result["summary"]["passed"] == 1


def test_run_sets_default_project_name_when_entry_point_missing(monkeypatch, tmp_path: Path):
    runner = EvaluationRunner(verbose=False)

    monkeypatch.setattr(runner, "_prepare_environment", lambda env, proj: {"absolute_path": str(tmp_path)})

    def _run_rule(rule_name, rule_config, artifact_info):
        from codegate.engine.result import RuleResult

        return RuleResult(rule_name=rule_name, passed=True, message="ok", details={}, duration=0.0)

    monkeypatch.setattr(runner, "_run_rule", _run_rule)

    contract = {
        "Environment": {},
        "project": {"path": str(tmp_path)},
        "rules": {"policy": {}},
    }

    result = runner.run(contract)
    assert result["project"] == "project"
