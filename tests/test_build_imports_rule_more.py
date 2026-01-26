"""Extra tests for the `build_imports` rule failure branches."""

from __future__ import annotations

from pathlib import Path

from codegate.rules.build_imports import Rule


def test_build_imports_no_docker_or_deps_image(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('x')\n")
    rule = Rule({})

    passed, message, details = rule.execute({"absolute_path": str(tmp_path), "docker_runner": None, "deps_image": None})
    assert passed is False
    assert "docker not available" in message.lower()


def test_build_imports_project_path_missing(tmp_path: Path):
    rule = Rule({})

    class _DR:
        pass

    passed, message, details = rule.execute({"absolute_path": str(tmp_path / 'missing'), "docker_runner": _DR(), "deps_image": "img"})
    assert passed is False
    assert "project path not found" in message.lower()
