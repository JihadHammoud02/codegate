"""
Unit Tests Rule - Run unit tests and check coverage.

This rule:
1. Runs pytest in the Docker container
2. Checks if all tests pass
3. Validates coverage meets threshold

Uses the pre-built deps_image from DockerRunner.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple

from .base import BaseRule


class Rule(BaseRule):
    """
    Unit tests rule implementation.
    
    Runs pytest with coverage in Docker container.
    """
    
    WORKSPACE_PATH = "/workspace"
    EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".tox", ".nox", ".venv", "venv"}

    @staticmethod
    def _is_relative_dir(value: str) -> bool:
        # Treat empty/./.\ as project root
        if value is None:
            return True
        v = str(value).strip()
        if v in ("", ".", "./"):
            return True
        # Absolute paths (host paths) should never be passed into the container
        return not v.startswith("/")
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the unit tests rule."""
        super().__init__(config)
        self.test_directory = config.get("test_directory", "tests/")
        self.coverage_threshold = config.get("coverage_threshold", 85)
        self.timeout = config.get("timeout", 300)
    
    def execute(self, artifact_info: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute unit tests.
        
        Args:
            artifact_info: Must contain:
                - docker_runner: DockerRunner instance
                - deps_image: Pre-built image with dependencies
                - absolute_path: Path to project
                - network_access: Network access flag
                
        Returns:
            Tuple of (passed, message, details)
        """
        docker_runner = artifact_info.get("docker_runner")
        deps_image = artifact_info.get("deps_image")
        project_path = Path(artifact_info.get("absolute_path", ""))
        network_access = artifact_info.get("network_access", False)
        
        details = {
            "test_directory": self.test_directory,
            "coverage_threshold": self.coverage_threshold,
            "tests_found": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "coverage_percentage": 0.0,
        }
        
        # Validate prerequisites
        if not docker_runner or not deps_image:
            return False, "Docker not available or deps image not built", details
        
        if not project_path.exists():
            return False, f"Project path not found: {project_path}", details
        
        # Check test directory exists (only allow relative dirs)
        test_dir_rel = str(self.test_directory).strip() if self.test_directory is not None else ""
        if not self._is_relative_dir(test_dir_rel):
            # Host absolute path provided -> fall back to project root
            test_dir_rel = ""

        if test_dir_rel in ("", ".", "./"):
            test_dir = project_path
        else:
            test_dir = project_path / test_dir_rel
            
        if not test_dir.exists():
            return False, f"Test directory not found: {self.test_directory}", details
        
        # Count test files
        test_files = [
            p
            for p in (list(test_dir.glob("test_*.py")) + list(test_dir.glob("*_test.py")))
            if not any(part in self.EXCLUDE_DIRS for part in p.parts)
        ]
        details["tests_found"] = len(test_files)
        
        if not test_files:
            return False, "No test files found", details
        
        try:
            # Run pytest with coverage (container path only)
            if test_dir_rel in ("", ".", "./"):
                test_path = self.WORKSPACE_PATH
            else:
                # avoid double slashes
                test_path = f"{self.WORKSPACE_PATH}/{test_dir_rel.lstrip('./')}"
            
            proc = docker_runner.run_command(
                image=deps_image,
                command=[
                    "python", "-m", "pytest",
                    test_path,
                    "-v", "--tb=short",
                    f"--cov={self.WORKSPACE_PATH}",
                    "--cov-report=term"
                ],
                project_path=project_path,
                network_access=network_access,
                writable=True,  # pytest-cov needs to write .coverage
                timeout=self.timeout
            )
            
            output = proc.stdout + proc.stderr
            details["test_output"] = output[-2000:]
            
            # Parse test results
            passed_match = re.search(r'(\d+) passed', output)
            if passed_match:
                details["tests_passed"] = int(passed_match.group(1))
            
            failed_match = re.search(r'(\d+) failed', output)
            if failed_match:
                details["tests_failed"] = int(failed_match.group(1))
            
            # Parse coverage percentage
            cov_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
            if cov_match:
                details["coverage_percentage"] = float(cov_match.group(1))
            
            # Determine result
            if proc.returncode != 0:
                if details["tests_failed"] > 0:
                    return False, f"{details['tests_failed']} test(s) failed", details
                else:
                    return False, "Tests failed", details
            
            # Check coverage threshold
            if details["coverage_percentage"] < self.coverage_threshold:
                return False, (
                    f"Coverage {details['coverage_percentage']:.1f}% "
                    f"below threshold {self.coverage_threshold}%"
                ), details
            
            return True, (
                f"All {details['tests_passed']} tests passed with "
                f"{details['coverage_percentage']:.1f}% coverage"
            ), details
            
        except subprocess.TimeoutExpired:
            return False, f"Tests timed out after {self.timeout}s", details
        except Exception as e:
            return False, f"Test execution failed: {str(e)}", details
