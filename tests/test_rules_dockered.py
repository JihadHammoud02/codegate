"""High-coverage unit tests for Docker-executed rules.

We don't actually spin up Docker.
Instead we provide a tiny fake DockerRunner that returns canned stdout/stderr.

This covers:
- build_imports
- unit_tests
- security_sast
- security_deps
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from codegate.rules.build_imports import Rule as BuildImportsRule
from codegate.rules.unit_tests import Rule as UnitTestsRule
from codegate.rules.security_sast import Rule as SecuritySastRule
from codegate.rules.security_deps import Rule as SecurityDepsRule


class FakeProc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeDockerRunner:
    def __init__(self, responses: List[FakeProc]):
        self._responses = list(responses)
        self.calls = []

    def run_command(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            return FakeProc(returncode=1, stdout="", stderr="No fake response configured")
        return self._responses.pop(0)


def _artifact(tmp_path: Path, runner: FakeDockerRunner) -> dict:
    (tmp_path / "main.py").write_text("print('hi')\n")
    return {
        "docker_runner": runner,
        "deps_image": "fake:deps",
        "absolute_path": str(tmp_path),
        "entry_point": "main.py",
        "network_access": False,
    }


def test_build_imports_happy_path(tmp_path: Path):
    runner = FakeDockerRunner(
        [
            FakeProc(0, stdout="", stderr=""),  # compileall
            FakeProc(0, stdout="IMPORT_OK\n", stderr=""),  # import
        ]
    )
    rule = BuildImportsRule({"import_timeout": 5})
    passed, msg, details = rule.execute(_artifact(tmp_path, runner))
    assert passed is True
    assert details["phases"]["compilation"]["success"] is True
    assert details["phases"]["entrypoint_import"]["success"] is True
    assert len(runner.calls) == 2


def test_build_imports_compile_failure(tmp_path: Path):
    runner = FakeDockerRunner([FakeProc(1, stdout="", stderr="SyntaxError: bad")])
    rule = BuildImportsRule({})
    passed, msg, details = rule.execute(_artifact(tmp_path, runner))
    assert passed is False
    assert "Compilation failed" in msg
    assert details["phases"]["compilation"]["success"] is False


def test_unit_tests_parses_counts_and_coverage(tmp_path: Path):
    # Ensure tests exist so rule doesn't early-exit
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_ok():\n    assert True\n")

    out = "collected 7 items\n\n7 passed in 0.01s\nTOTAL 10 0 90%\n"
    runner = FakeDockerRunner([FakeProc(0, stdout=out, stderr="")])
    rule = UnitTestsRule({"test_directory": "tests/", "coverage_threshold": 80})
    passed, msg, details = rule.execute({
        "docker_runner": runner,
        "deps_image": "fake:deps",
        "absolute_path": str(tmp_path),
        "network_access": False,
    })

    assert passed is True
    assert details["tests_found"] == 7
    assert details["tests_passed"] == 7
    assert details["coverage_percentage"] == 90.0


def test_unit_tests_fails_below_coverage(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_ok():\n    assert True\n")

    out = "collected 1 items\n\n1 passed in 0.01s\nTOTAL 10 5 50%\n"
    runner = FakeDockerRunner([FakeProc(0, stdout=out, stderr="")])
    rule = UnitTestsRule({"test_directory": "tests/", "coverage_threshold": 80})
    passed, msg, details = rule.execute({
        "docker_runner": runner,
        "deps_image": "fake:deps",
        "absolute_path": str(tmp_path),
        "network_access": False,
    })

    assert passed is False
    assert "below threshold" in msg


def test_security_sast_no_issues(tmp_path: Path):
    runner = FakeDockerRunner([FakeProc(0, stdout=json.dumps({"results": []}), stderr="")])
    rule = SecuritySastRule({})
    passed, msg, details = rule.execute(_artifact(tmp_path, runner))
    assert passed is True
    assert details["issues_found"] == 0


def test_security_sast_fails_on_high(tmp_path: Path):
    payload = {
        "results": [
            {
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "issue_text": "bad",
                "filename": "/workspace/main.py",
                "line_number": 1,
            }
        ]
    }
    runner = FakeDockerRunner([FakeProc(0, stdout=json.dumps(payload), stderr="")])
    rule = SecuritySastRule({})
    passed, msg, details = rule.execute(_artifact(tmp_path, runner))
    assert passed is False
    assert "high severity" in msg.lower()
    assert details["high_severity"] == 1


def test_security_deps_no_vulns(tmp_path: Path):
    # security_deps may call pip-audit and parse; we just return empty findings.
    runner = FakeDockerRunner([FakeProc(0, stdout=json.dumps({"dependencies": [], "vulnerabilities": []}), stderr="")])
    rule = SecurityDepsRule({})
    passed, msg, details = rule.execute(_artifact(tmp_path, runner))
    assert passed is True
