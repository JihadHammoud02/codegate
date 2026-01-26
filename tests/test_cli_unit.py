"""In-process unit tests for `codegate.cli`.

We do this (in addition to subprocess smoke tests) to actually count coverage for
`codegate/cli.py` under pytest-cov.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import codegate.cli as cli


def test_run_contract_missing_file_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    missing = tmp_path / "missing.yaml"
    rc = cli.run_contract(str(missing), str(tmp_path / "out.json"), verbose=False)
    assert rc == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


def test_run_contract_happy_path_writes_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text("Environment: {runtime_image: python:3.11-slim}\nproject: {path: .}\nrules: {}\n")

    out = tmp_path / "out.json"

    class _FakeParser:
        def parse(self, p: Path):
            assert p == contract_path
            return {"Environment": {"runtime_image": "python:3.11-slim"}, "project": {"path": "."}, "rules": {}}

    class _FakeRunner:
        def __init__(self, verbose: bool = False):
            self.verbose = verbose

        def run(self, contract):
            return {
                "summary": {"passed": 0, "failed": 0},
                "results": [],
            }

    monkeypatch.setattr(cli, "ContractParser", _FakeParser)
    monkeypatch.setattr(cli, "EvaluationRunner", _FakeRunner)

    rc = cli.run_contract(str(contract_path), str(out), verbose=True)
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["summary"]["failed"] == 0


def test_run_contract_returns_1_when_failed_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text("Environment: {runtime_image: python:3.11-slim}\nproject: {path: .}\nrules: {}\n")

    out = tmp_path / "out.json"

    class _FakeParser:
        def parse(self, p: Path):
            return {"Environment": {"runtime_image": "python:3.11-slim"}, "project": {"path": "."}, "rules": {}}

    class _FakeRunner:
        def __init__(self, verbose: bool = False):
            self.verbose = verbose

        def run(self, contract):
            return {
                "summary": {"passed": 1, "failed": 2},
                "results": [],
            }

    monkeypatch.setattr(cli, "ContractParser", _FakeParser)
    monkeypatch.setattr(cli, "EvaluationRunner", _FakeRunner)

    rc = cli.run_contract(str(contract_path), str(out), verbose=False)
    assert rc == 1


def test_main_version(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    monkeypatch.setattr(cli.sys, "argv", ["codegate", "version"])
    rc = cli.main()
    assert rc == 0
    assert "CodeGate version" in capsys.readouterr().out


def test_main_no_command(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cli.sys, "argv", ["codegate"])
    rc = cli.main()
    assert rc == 1
