"""Additional tests to cover EvaluationRunner branches.

Focus:
- disabled rules are skipped
- unknown rules -> import error path -> failure RuleResult
- rule exceptions are caught and returned as failure
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from codegate.engine.runner import EvaluationRunner


def _base_contract(project_path: Path):
    return {
        "Environment": {"runtime_image": "python:3.11-slim", "network_access": False},
        "project": {"path": str(project_path), "entry_point": "main.py"},
        "rules": {},
    }


def test_runner_skips_disabled_rules(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    contract = _base_contract(tmp_path)
    contract["rules"] = {
        "policy": {"enabled": False},
    }

    runner = EvaluationRunner(verbose=False)
    results = runner.run(contract)

    assert results["summary"]["total"] == 0
    assert results["results"] == []


def test_runner_unknown_rule_import_error_returns_failure(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    contract = _base_contract(tmp_path)
    contract["rules"] = {"nonexistent_rule": {"enabled": True}}

    runner = EvaluationRunner(verbose=False)
    results = runner.run(contract)

    assert results["summary"]["total"] == 1
    assert results["summary"]["failed"] == 1
    assert results["results"][0]["rule"] == "nonexistent_rule"
    assert results["results"][0]["passed"] is False
    assert "not found" in results["results"][0]["message"].lower()


def test_runner_rule_exception_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "main.py").write_text("print('x')\n")

    contract = _base_contract(tmp_path)
    contract["rules"] = {"policy": {"enabled": True}}

    runner = EvaluationRunner(verbose=False)

    # Patch policy module loader to return a dummy rule that raises.
    m = types.SimpleNamespace()

    class BoomRule:
        def __init__(self, config):
            pass

        def execute(self, artifact_info):
            raise RuntimeError("boom")

    m.Rule = BoomRule

    monkeypatch.setattr(runner, "_load_rule_module", lambda name: m)

    results = runner.run(contract)

    assert results["summary"]["failed"] == 1
    assert "boom" in results["results"][0]["message"].lower()
