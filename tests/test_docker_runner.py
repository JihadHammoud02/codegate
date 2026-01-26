"""Unit tests for DockerRunner.

These tests don't require Docker to be installed; when Docker isn't present,
we validate that CodeGate behaves gracefully.
"""

from __future__ import annotations

import sys

import pytest

from codegate.engine.docker_runner import DockerRunner


def test_is_available_returns_bool():
    runner = DockerRunner(verbose=False)
    assert isinstance(runner.is_available(), bool)


def test_run_command_raises_when_docker_missing(monkeypatch: pytest.MonkeyPatch):
    runner = DockerRunner(verbose=False)

    # Force "not available" regardless of machine setup.
    monkeypatch.setattr(runner, "is_available", lambda: False)

    with pytest.raises(RuntimeError):
        runner.run_command(image="python:3.11-slim", command=[sys.executable, "-c", "print('x')"])
