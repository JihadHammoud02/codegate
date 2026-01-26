"""One big, end-to-end test that exercises the whole project.

Goal:
- Cover CLI -> contract parsing -> runner orchestration -> rule modules
- Stay fully offline and not require Docker

Strategy:
- Create a temporary project directory
- Write a contract.yaml for that project
- Monkeypatch DockerRunner methods so rules execute through mocked container runs
- Invoke the CLI as a subprocess (`python -m codegate.cli run ...`) and assert on JSON output

This test is intentionally broad to drive coverage quickly.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest


class _FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _install_test_shims(monkeypatch: pytest.MonkeyPatch, project_root: Path) -> None:
    """Patch DockerRunner so the engine/rules think they're using Docker.

    We emulate the few commands our built-in rules actually call.
    """

    from codegate.engine import docker_runner as dr

    def fake_check_available(self) -> None:
        return None

    def fake_is_available(self) -> bool:
        return True

    def fake_build_deps_image(self, runtime_image: str, system_dependencies: List[str], python_dependencies: List[str], project_path: Path) -> str:
        # Return a deterministic tag.
        assert runtime_image
        assert project_path.exists()
        return "codegate-test:deps"

    def fake_run_command(
        self,
        image: str,
        command: List[str],
        project_path: Path | None = None,
        network_access: bool = False,
        writable: bool = False,
        environment: Dict[str, str] | None = None,
        timeout: int = 120,
        memory_limit: str = "512m",
        cpu_limit: str = "1",
    ):
        assert image
        assert isinstance(command, list) and command

        # Most rules mount the project and run from /workspace.
        # We'll execute an equivalent host operation and return a CompletedProcess-like object.

        # build_imports: python -m compileall ... /workspace or '.'
        if command[:3] == ["python", "-m", "compileall"]:
            # Just ensure the files can be compiled.
            import compileall

            ok = compileall.compile_dir(str(project_root), quiet=1)
            return _FakeCompleted(returncode=0 if ok else 1, stdout="", stderr="" if ok else "compile failed")

        # build_imports: python -c "import importlib; importlib.import_module('...')"
        if command[:2] == ["python", "-c"] and "importlib.import_module" in command[2]:
            # Evaluate the import in a subprocess with PYTHONPATH pointing at the project root.
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)
            proc = subprocess.run(
                [sys.executable, "-c", command[2]],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            return _FakeCompleted(proc.returncode, proc.stdout, proc.stderr)

        # unit_tests: python -m pytest ... --cov=...
        if command[:3] == ["python", "-m", "pytest"]:
            # We don't need real coverage here; we just need deterministic output that the rule parses.
            # Make it look like pytest ran tests.
            fake = """
============================= test session starts =============================
collected 3 items

foo_test.py ...                                                        [100%]

================================== coverage ==================================
TOTAL 10 0 100%

3 passed in 0.02s
"""
            return _FakeCompleted(0, stdout=fake, stderr="")

        # security_sast: bandit
        if (command and "bandit" in command[0]) or (len(command) >= 3 and command[:2] == ["python", "-m"] and command[2] == "bandit"):
            # Produce empty JSON results.
            return _FakeCompleted(0, stdout=json.dumps({"results": []}), stderr="")

        # security_deps: pip-audit
        if command and ("pip-audit" in command[0] or command[:2] == ["python", "-m"] and "pip_audit" in command[2]):
            # No vulnerabilities.
            return _FakeCompleted(0, stdout=json.dumps({"dependencies": [], "vulnerabilities": []}), stderr="")

        return _FakeCompleted(1, stdout="", stderr=f"Unexpected command: {command}")

    monkeypatch.setattr(dr.DockerRunner, "check_available", fake_check_available, raising=True)
    monkeypatch.setattr(dr.DockerRunner, "is_available", fake_is_available, raising=True)
    monkeypatch.setattr(dr.DockerRunner, "build_deps_image", fake_build_deps_image, raising=True)
    monkeypatch.setattr(dr.DockerRunner, "run_command", fake_run_command, raising=True)


def test_big_end_to_end_contract_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    # Arrange: tiny project
    project_root = tmp_path / "proj"
    project_root.mkdir()

    (project_root / "__init__.py").write_text("\n")
    (project_root / "main.py").write_text(
        """
import math

def add(a, b):
    return a + b

def area(r):
    return math.pi * r * r
""".lstrip()
    )

    # A minimal test file (won't actually be executed; unit_tests is mocked)
    tests_dir = project_root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_dummy():\n    assert 1 + 1 == 2\n")

    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text(
        """
Environment:
  runtime_image: python:3.11-slim
  network_access: false

project:
  path: ./proj
  entry_point: main.py
  python_dependencies: ["pytest", "pytest-cov", "bandit", "pip-audit"]

rules:
  build_imports:
    enabled: true
  unit_tests:
    enabled: true
    test_directory: tests/
    coverage_threshold: 80
  security_sast:
    enabled: true
  security_deps:
    enabled: true
  policy:
    enabled: true
    forbidden_apis: ["eval", "exec"]
""".lstrip()
    )

    # Patch DockerRunner inside this test process (CLI runs as subprocess).
    # We'll use PYTHONPATH to point at a shim module that applies patches on import.
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    (shim_dir / "sitecustomize.py").write_text(
        (
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "# In subprocesses, start coverage first (COVERAGE_PROCESS_START is set by the test).\n"
            "try:\n"
            "    import coverage\n"
            "    coverage.process_startup()\n"
            "except Exception:\n"
            "    pass\n"
            "\n"
            "# This file is automatically imported by Python on startup when present on PYTHONPATH.\n"
            "# It patches DockerRunner for the subprocess CLI invocation.\n"
            "\n"
            "def _apply():\n"
            "    from codegate.engine import docker_runner as dr\n"
            "\n"
            "    class _FakeCompleted:\n"
            "        def __init__(self, returncode=0, stdout='', stderr=''):\n"
            "            self.returncode = returncode\n"
            "            self.stdout = stdout\n"
            "            self.stderr = stderr\n"
            "\n"
            "    project_root = Path(os.environ.get('CODEGATE_TEST_PROJECT_ROOT', '.')).resolve()\n"
            "\n"
            "    def fake_check_available(self):\n"
            "        return None\n"
            "    def fake_is_available(self):\n"
            "        return True\n"
            "    def fake_build_deps_image(self, runtime_image, system_dependencies, python_dependencies, project_path):\n"
            "        return 'codegate-test:deps'\n"
            "\n"
            "    def fake_run_command(self, image, command, project_path=None, network_access=False, writable=False, environment=None, timeout=120, memory_limit='512m', cpu_limit='1'):\n"
            "        import json, subprocess, sys, compileall\n"
            "        if command[:3] == ['python','-m','compileall']:\n"
            "            ok = compileall.compile_dir(str(project_root), quiet=1)\n"
            "            return _FakeCompleted(0 if ok else 1, '', '' if ok else 'compile failed')\n"
            "        if command[:2] == ['python','-c'] and 'importlib.import_module' in command[2]:\n"
            "            env = os.environ.copy()\n"
            "            env['PYTHONPATH'] = str(project_root)\n"
            "            p = subprocess.run([sys.executable,'-c',command[2]], cwd=str(project_root), capture_output=True, text=True, env=env)\n"
            "            return _FakeCompleted(p.returncode, p.stdout, p.stderr)\n"
            "        if command[:3] == ['python','-m','pytest']:\n"
            "            fake = 'collected 3 items\\n\\n3 passed in 0.02s\\nTOTAL 10 0 100%\\n'\n"
            "            return _FakeCompleted(0, fake, '')\n"
            "        if (command and 'bandit' in command[0]) or (len(command) >= 3 and command[:2] == ['python','-m'] and command[2] == 'bandit'):\n"
            "            return _FakeCompleted(0, json.dumps({'results': []}), '')\n"
            "        if command and ('pip-audit' in command[0]):\n"
            "            return _FakeCompleted(0, json.dumps({'dependencies': [], 'vulnerabilities': []}), '')\n"
            "        return _FakeCompleted(1, '', 'Unexpected command: %s' % command)\n"
            "\n"
            "    dr.DockerRunner.check_available = fake_check_available\n"
            "    dr.DockerRunner.is_available = fake_is_available\n"
            "    dr.DockerRunner.build_deps_image = fake_build_deps_image\n"
            "    dr.DockerRunner.run_command = fake_run_command\n"
            "\n"
            "_apply()\n"
        )
    )

    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = f"{shim_dir}:{repo_root}/tests:{repo_root}:{env.get('PYTHONPATH','')}"
    env["CODEGATE_TEST_PROJECT_ROOT"] = str(project_root)
    env["COVERAGE_PROCESS_START"] = str(repo_root / "pyproject.toml")

    # Act
    output_file = tmp_path / "out.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "codegate.cli",
            "run",
            str(contract_path),
            "--output",
            str(output_file),
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    # Assert
    # CLI returns non-zero if any rule fails.
    # We expect success here.
    if proc.returncode != 0:
        diag = (proc.stdout + "\n" + proc.stderr).strip()
        if output_file.exists():
            try:
                diag_data = json.loads(output_file.read_text())
                diag += f"\nOutput summary: {diag_data.get('summary')}"
                failed = [r for r in diag_data.get('results', []) if not r.get('passed')]
                if failed:
                    diag += f"\nFailed rules: {[f.get('rule') for f in failed]}"
            except Exception:
                pass
        assert proc.returncode == 0, diag

    # CLI writes results as JSON to the output file (stdout is a human summary).
    # Use explicit output file to keep test isolated.
    assert output_file.exists(), (proc.stdout + "\n" + proc.stderr)
    data = json.loads(output_file.read_text())
    assert "summary" in data
    assert data["summary"]["failed"] == 0
    assert data["summary"]["passed"] >= 3

    by_rule = {r["rule"]: r for r in data.get("results", [])}
    # sanity: at least these rules should exist
    assert "policy" in by_rule
    assert "build_imports" in by_rule
    assert "unit_tests" in by_rule
