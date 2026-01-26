"""Extra tests for security rules edge paths.

We aim to cover early error paths + JSON decode fallback branches.
"""

from __future__ import annotations

import json
from pathlib import Path

from codegate.rules.security_sast import Rule as SastRule
from codegate.rules.security_deps import Rule as DepsRule


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_security_sast_skips_when_bandit_missing(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    class _DR:
        def run_command(self, **kwargs):
            return _Proc(0, stdout="not json", stderr="No module named bandit")

    rule = SastRule({})
    passed, message, details = rule.execute({"absolute_path": str(tmp_path), "docker_runner": _DR(), "deps_image": "img"})

    assert passed is True
    assert "skipped" in message.lower() or "not available" in message.lower()


def test_security_sast_fails_on_high_severity(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    bandit_out = json.dumps({"results": [{"issue_severity": "HIGH", "issue_text": "bad", "filename": "/workspace/main.py", "line_number": 1}]})

    class _DR:
        def run_command(self, **kwargs):
            return _Proc(0, stdout=bandit_out, stderr="")

    rule = SastRule({})
    passed, message, details = rule.execute({"absolute_path": str(tmp_path), "docker_runner": _DR(), "deps_image": "img"})

    assert passed is False
    assert details["high_severity"] == 1


def test_security_deps_fails_when_project_path_missing(tmp_path: Path):
    missing = tmp_path / "missing"

    class _DR:
        pass

    rule = DepsRule({})
    passed, message, details = rule.execute({"absolute_path": str(missing), "docker_runner": _DR(), "deps_image": "img"})

    assert passed is False
    assert "project path not found" in message.lower()
