from __future__ import annotations

from pathlib import Path

import pytest

from codegate.rules.build_imports import Rule


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_build_imports_compilation_failure_is_reported(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('x')\n")

    class _DR:
        def run_command(self, **kwargs):
            # compileall failed
            return _Proc(returncode=1, stdout="", stderr="SyntaxError: invalid syntax")

    rule = Rule({"import_timeout": 1})

    passed, message, details = rule.execute(
        {
            "docker_runner": _DR(),
            "deps_image": "img",
            "absolute_path": str(tmp_path),
            "entry_point": "a.py",
        }
    )

    assert passed is False
    assert "Compilation failed" in message
    assert details["phases"]["compilation"]["success"] is False


def test_build_imports_import_phase_skipped_when_no_entry_point(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('x')\n")

    class _DR:
        def run_command(self, **kwargs):
            # compileall ok
            return _Proc(returncode=0, stdout="", stderr="")

    rule = Rule({"import_timeout": 1})

    passed, message, details = rule.execute(
        {
            "docker_runner": _DR(),
            "deps_image": "img",
            "absolute_path": str(tmp_path),
            "entry_point": "",
        }
    )

    assert passed is True
    assert details["phases"]["entrypoint_import"]["success"] is True
    assert "skipped" in details["phases"]["entrypoint_import"]["note"].lower()


def test_build_imports_import_failure_is_reported(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('x')\n")

    calls = {"n": 0}

    class _DR:
        def run_command(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                # compileall ok
                return _Proc(returncode=0, stdout="", stderr="")
            # import fails
            return _Proc(returncode=1, stdout="", stderr="ModuleNotFoundError: No module named 'a'")

    rule = Rule({"import_timeout": 1})

    passed, message, details = rule.execute(
        {
            "docker_runner": _DR(),
            "deps_image": "img",
            "absolute_path": str(tmp_path),
            "entry_point": "a.py",
        }
    )

    assert passed is False
    assert "Import failed" in message
    assert details["phases"]["entrypoint_import"]["success"] is False


def test_build_imports_import_timeout_returns_timeout_message(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('x')\n")

    calls = {"n": 0}

    class _DR:
        def run_command(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return _Proc(returncode=0, stdout="", stderr="")
            raise pytest.importorskip("subprocess").TimeoutExpired(cmd="x", timeout=1)

    rule = Rule({"import_timeout": 1})

    passed, message, details = rule.execute(
        {
            "docker_runner": _DR(),
            "deps_image": "img",
            "absolute_path": str(tmp_path),
            "entry_point": "a.py",
        }
    )

    assert passed is False
    assert "timed out" in message.lower()
