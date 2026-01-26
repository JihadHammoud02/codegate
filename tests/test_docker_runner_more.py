from __future__ import annotations

from pathlib import Path

import pytest

from codegate.engine.docker_runner import DockerRunner


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_is_available_false_when_docker_missing(monkeypatch):
    runner = DockerRunner()

    def _run(*args, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr("codegate.engine.docker_runner.subprocess.run", _run)

    assert runner.is_available() is False


def test_build_deps_image_uses_cache_when_image_exists(monkeypatch, tmp_path: Path):
    runner = DockerRunner(verbose=True)

    monkeypatch.setattr(runner, "check_available", lambda: None)
    monkeypatch.setattr(runner, "_hash_config", lambda *a, **k: "abc123" * 10)
    monkeypatch.setattr(runner, "_image_exists", lambda tag: True)

    tag = runner.build_deps_image(
        runtime_image="python:3.12-slim",
        system_dependencies=["git"],
        python_dependencies=["requests"],
        project_path=tmp_path,
        force_rebuild=False,
    )

    assert tag.startswith("codegate-deps:")
    assert runner._deps_image == tag


def test_build_deps_image_force_rebuild_runs_docker_build(monkeypatch, tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask==2.0.0\n")

    runner = DockerRunner(verbose=False)
    monkeypatch.setattr(runner, "check_available", lambda: None)
    monkeypatch.setattr(runner, "_hash_config", lambda *a, **k: "deadbeef" * 8)
    monkeypatch.setattr(runner, "_image_exists", lambda tag: True)

    calls = {"build": 0}

    def _run(cmd, capture_output=False, text=False, timeout=None):
        if cmd[:2] == ["docker", "build"]:
            calls["build"] += 1
            return _Proc(0, stdout="ok", stderr="")
        return _Proc(0, stdout="", stderr="")

    monkeypatch.setattr("codegate.engine.docker_runner.subprocess.run", _run)

    tag = runner.build_deps_image(
        runtime_image="python:3.12-slim",
        system_dependencies=[],
        python_dependencies=["requests"],
        project_path=tmp_path,
        force_rebuild=True,
    )

    assert calls["build"] == 1
    assert runner._deps_image == tag


def test_build_deps_image_raises_runtime_error_on_build_failure(monkeypatch, tmp_path: Path):
    runner = DockerRunner(verbose=False)
    monkeypatch.setattr(runner, "check_available", lambda: None)
    monkeypatch.setattr(runner, "_hash_config", lambda *a, **k: "fff" * 30)
    monkeypatch.setattr(runner, "_image_exists", lambda tag: False)
    monkeypatch.setattr(runner, "_parse_build_error", lambda stderr: "nice error")

    def _run(cmd, capture_output=False, text=False, timeout=None):
        if cmd[:2] == ["docker", "build"]:
            return _Proc(1, stdout="", stderr="raw")
        return _Proc(0, stdout="", stderr="")

    monkeypatch.setattr("codegate.engine.docker_runner.subprocess.run", _run)

    with pytest.raises(RuntimeError) as exc:
        runner.build_deps_image(
            runtime_image="python:3.12-slim",
            system_dependencies=[],
            python_dependencies=[],
            project_path=tmp_path,
            force_rebuild=True,
        )

    assert "Docker build failed" in str(exc.value)
    assert "nice error" in str(exc.value)


def test_parse_build_error_picks_error_lines():
    runner = DockerRunner()

    assert runner._parse_build_error("ERROR: boom\n") == "ERROR: boom"
    assert "No matching distribution" in runner._parse_build_error("No matching distribution found for x")


def test_generate_dockerfile_includes_system_deps_and_requirements():
    runner = DockerRunner()

    df = runner._generate_dockerfile(
        runtime_image="python:3.12-slim",
        system_dependencies=["git", "curl"],
        has_requirements=True,
    )

    assert df.startswith("FROM python:3.12-slim")
    assert "apt-get install" in df
    assert "COPY requirements.txt" in df


def test_image_exists_false_on_exception(monkeypatch):
    runner = DockerRunner()

    def _run(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("codegate.engine.docker_runner.subprocess.run", _run)

    assert runner._image_exists("x") is False
