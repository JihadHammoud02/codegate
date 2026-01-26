"""Coverage-oriented tests for DockerRunner command construction.

We don't want to run real Docker here. Instead we monkeypatch subprocess.run
and assert the command line is what we expect.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codegate.engine.docker_runner import DockerRunner


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_command_builds_expected_flags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    runner = DockerRunner(verbose=False)

    # Force docker availability.
    monkeypatch.setattr(runner, "check_available", lambda: None)

    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return _Proc(0, "ok", "")

    monkeypatch.setattr("codegate.engine.docker_runner.subprocess.run", fake_run)

    project = tmp_path
    proc = runner.run_command(
        image="python:3.11-slim",
        command=["python", "-c", "print('hi')"],
        project_path=project,
        network_access=False,
        writable=False,
        environment={"FOO": "bar"},
        timeout=5,
        memory_limit="256m",
        cpu_limit="0.5",
    )

    assert proc.returncode == 0
    cmd = captured["cmd"]

    # docker run --rm
    assert cmd[:3] == ["docker", "run", "--rm"]
    # network none when disabled
    assert "--network=none" in cmd
    # limits
    assert "--memory=256m" in cmd
    assert "--cpus=0.5" in cmd
    # mount
    assert "-v" in cmd
    mount = cmd[cmd.index("-v") + 1]
    assert mount.endswith(f":{runner.WORKSPACE_PATH}:ro")
    # env
    assert "-e" in cmd
    assert "FOO=bar" in cmd
    # image + command must be at end
    assert "python:3.11-slim" in cmd
    assert cmd[-3:] == ["python", "-c", "print('hi')"]


def test_run_command_mount_rw(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    runner = DockerRunner(verbose=False)
    monkeypatch.setattr(runner, "check_available", lambda: None)

    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return _Proc(0, "ok", "")

    monkeypatch.setattr("codegate.engine.docker_runner.subprocess.run", fake_run)

    runner.run_command(
        image="python:3.11-slim",
        command=["echo", "x"],
        project_path=tmp_path,
        writable=True,
        network_access=True,
    )

    cmd = captured["cmd"]
    # network flag absent when enabled
    assert "--network=none" not in cmd

    mount = cmd[cmd.index("-v") + 1]
    assert mount.endswith(f":{runner.WORKSPACE_PATH}:rw")
