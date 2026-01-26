from __future__ import annotations

import json
from pathlib import Path

import pytest

from codegate.rules.security_deps import Rule


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_security_deps_skips_when_no_scanner_available(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    class _DR:
        def __init__(self):
            self.calls = 0

        def run_command(self, **kwargs):
            self.calls += 1
            # Both pip-audit and safety report missing
            return _Proc(0, stdout="", stderr="No module named whatever")

    dr = _DR()
    rule = Rule({"timeout": 1})

    passed, message, details = rule.execute(
        {
            "docker_runner": dr,
            "deps_image": "img",
            "absolute_path": str(tmp_path),
            "network_access": False,
            "python_dependencies": ["a", "b"],
        }
    )

    assert passed is True
    assert "skipped" in message.lower()
    assert details["scanner"] is None
    assert dr.calls == 2


def test_security_deps_pip_audit_reports_vulnerabilities(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    audit_json = json.dumps(
        {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.0",
                    "vulns": [{"id": "CVE-1", "description": "x" * 500}],
                }
            ]
        }
    )

    class _DR:
        def run_command(self, **kwargs):
            # pip-audit is present and returns JSON
            return _Proc(0, stdout=audit_json, stderr="")

    rule = Rule({"timeout": 1})

    passed, message, details = rule.execute(
        {
            "docker_runner": _DR(),
            "deps_image": "img",
            "absolute_path": str(tmp_path),
            "python_dependencies": ["requests"],
        }
    )

    assert passed is False
    assert details["scanner"] == "pip-audit"
    assert details["vulnerabilities_found"] == 1
    assert details["vulnerable_packages"][0]["name"] == "requests"
    # description should be truncated
    assert len(details["vulnerable_packages"][0]["description"]) <= 200


def test_security_deps_pip_audit_invalid_json_is_treated_as_no_vulns(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    class _DR:
        def run_command(self, **kwargs):
            return _Proc(0, stdout="not json", stderr="")

    rule = Rule({"timeout": 1})

    passed, message, details = rule.execute(
        {
            "docker_runner": _DR(),
            "deps_image": "img",
            "absolute_path": str(tmp_path),
        }
    )

    assert passed is True
    assert details["scanner"] == "pip-audit"
    assert details["vulnerabilities_found"] == 0


def test_security_deps_timeout_is_handled(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    class _DR:
        def run_command(self, **kwargs):
            raise TimeoutError("boom")

    rule = Rule({"timeout": 1})

    # The rule catches subprocess.TimeoutExpired specifically.
    # Make sure we raise that one.
    class _DR2:
        def run_command(self, **kwargs):
            raise pytest.importorskip("subprocess").TimeoutExpired(cmd="x", timeout=1)

    passed, message, details = rule.execute(
        {
            "docker_runner": _DR2(),
            "deps_image": "img",
            "absolute_path": str(tmp_path),
        }
    )

    assert passed is False
    assert "timed out" in message.lower()
