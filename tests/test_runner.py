"""
Tests for rule runner.
"""

import pytest
from pathlib import Path
import tempfile

from codegate.engine.runner import EvaluationRunner


def test_run_simple_contract():
    """Test running a simple contract."""
    # Create a simple Python file
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()
        
        test_file = src_dir / "test.py"
        test_file.write_text("print('Hello, world!')\n")
        
        contract = {
            "Environment": {
                "runtime_image": "python:3.11-slim",
                "network_access": False,
            },
            "project": {
                "path": str(src_dir),
                "entry_point": "test.py",
            },
            "rules": {
                # policy rule is local/static analysis and can run without Docker
                "policy": {
                    "enabled": True,
                    "forbidden_apis": ["eval"],
                }
            },
        }
        
        runner = EvaluationRunner(verbose=False)
        results = runner.run(contract)
        
        assert "summary" in results
        assert results["summary"]["total"] >= 1
        assert "results" in results


def test_run_disabled_rule():
    """Test that disabled rules are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()
        
        test_file = src_dir / "test.py"
        test_file.write_text("print('Hello')\n")
        
        contract = {
            "Environment": {
                "runtime_image": "python:3.11-slim",
                "network_access": False,
            },
            "project": {
                "path": str(src_dir),
                "entry_point": "test.py",
            },
            "rules": {
                "policy": {
                    "enabled": False,
                }
            },
        }
        
        runner = EvaluationRunner(verbose=False)
        results = runner.run(contract)
        
    assert results["summary"]["total"] == 0
