"""Extra tests for the `unit_tests` rule branches.

We cover the early-return failure cases that aren't hit by the happy-path tests.
"""

from __future__ import annotations

from pathlib import Path

from codegate.rules.unit_tests import Rule


def test_unit_tests_rule_no_docker_or_deps_image(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n")

    rule = Rule({"enabled": True})
    passed, message, details = rule.execute(
        {
            "absolute_path": str(tmp_path),
            "docker_runner": None,
            "deps_image": None,
        }
    )

    assert passed is False
    assert "docker not available" in message.lower()


def test_unit_tests_rule_missing_project_path(tmp_path: Path):
    missing = tmp_path / "missing"
    rule = Rule({"enabled": True})

    class _DR:
        pass

    passed, message, details = rule.execute(
        {
            "absolute_path": str(missing),
            "docker_runner": _DR(),
            "deps_image": "img",
        }
    )

    assert passed is False
    assert "project path not found" in message.lower()


def test_unit_tests_rule_missing_test_directory(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")

    class _DR:
        pass

    rule = Rule({"test_directory": "tests/"})
    passed, message, details = rule.execute(
        {
            "absolute_path": str(tmp_path),
            "docker_runner": _DR(),
            "deps_image": "img",
        }
    )

    assert passed is False
    assert "test directory not found" in message.lower()


def test_unit_tests_rule_no_test_files_found(tmp_path: Path):
    (tmp_path / "tests").mkdir()

    class _DR:
        pass

    rule = Rule({"test_directory": "tests/"})
    passed, message, details = rule.execute(
        {
            "absolute_path": str(tmp_path),
            "docker_runner": _DR(),
            "deps_image": "img",
        }
    )

    assert passed is False
    assert "no test files" in message.lower()
