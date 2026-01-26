"""CLI smoke tests.

We keep these tests lightweight and fully offline.
They validate argument parsing + graceful failure modes without requiring Docker.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_help_exits_zero():
    proc = subprocess.run(
        [sys.executable, "-m", "codegate.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "CodeGate" in (proc.stdout + proc.stderr)


def test_cli_missing_contract_exits_nonzero(tmp_path: Path):
    missing = tmp_path / "missing.yaml"
    proc = subprocess.run(
        [sys.executable, "-m", "codegate.cli", "run", str(missing)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "not found" in (proc.stdout + proc.stderr).lower()
