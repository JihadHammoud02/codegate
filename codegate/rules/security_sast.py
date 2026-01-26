"""
Security SAST Rule - Static Application Security Testing.

This rule runs bandit security scanner to detect:
- Hard-coded passwords
- SQL injection vulnerabilities  
- Use of insecure functions
- Other security issues

Uses the pre-built deps_image from DockerRunner.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple

from .base import BaseRule


class Rule(BaseRule):
    """
    Security SAST rule implementation.
    
    Runs bandit security scanner in Docker container.
    """
    
    WORKSPACE_PATH = "/workspace"
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the security SAST rule."""
        super().__init__(config)
        self.timeout = config.get("timeout", 120)
    
    def execute(self, artifact_info: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute SAST security scanning.
        
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
            "scanner": "bandit",
            "issues_found": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0,
            "issues": []
        }
        
        
        try:
            # Run bandit security scan
            proc = docker_runner.run_command(
                image=deps_image,
                command=[
                    "python", "-m", "bandit",
                    "-r", self.WORKSPACE_PATH,
                    "-f", "json",
                    "-ll"  # Low level and above
                ],
                project_path=project_path,
                network_access=network_access,
                timeout=self.timeout
            )
            
            # Try to parse JSON output
            try:
                bandit_data = json.loads(proc.stdout)
                results = bandit_data.get("results", [])
                details["issues_found"] = len(results)
                
                for issue in results:
                    severity = issue.get("issue_severity", "UNKNOWN").upper()
                    
                    if severity == "HIGH":
                        details["high_severity"] += 1
                    elif severity == "MEDIUM":
                        details["medium_severity"] += 1
                    elif severity == "LOW":
                        details["low_severity"] += 1
                    
                    details["issues"].append({
                        "severity": severity,
                        "confidence": issue.get("issue_confidence", "UNKNOWN"),
                        "text": issue.get("issue_text", ""),
                        "file": issue.get("filename", "").replace(self.WORKSPACE_PATH + "/", ""),
                        "line": issue.get("line_number", 0)
                    })
                
                # Fail on high severity
                if details["high_severity"] > 0:
                    return False, (
                        f"Found {details['high_severity']} high severity security issue(s)"
                    ), details
                
                # Pass with warnings for medium/low
                if details["issues_found"] > 0:
                    return True, (
                        f"Passed with {details['medium_severity']} medium and "
                        f"{details['low_severity']} low severity warnings"
                    ), details
                
                return True, "No security issues found", details
                
            except json.JSONDecodeError:
                # Bandit may not be installed
                if "No module named" in proc.stderr:
                    details["warning"] = "bandit not installed in deps image"
                    return True, "SAST scanner (bandit) not available, skipped", details
                
                # Other error
                output = proc.stdout + proc.stderr
                if "No issues identified" in output:
                    return True, "No security issues found", details
                
                details["raw_output"] = output[-500:]
                return False, "Security scan failed to parse output", details
                
        except subprocess.TimeoutExpired:
            return False, f"Security scan timed out after {self.timeout}s", details
        except Exception as e:
            return False, f"Security scan failed: {str(e)}", details
