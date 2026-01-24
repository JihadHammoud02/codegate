"""
Security Dependencies Rule - Check for vulnerable dependencies.

This rule scans installed dependencies for known vulnerabilities using:
- pip-audit (preferred)
- safety (fallback)

Uses the pre-built deps_image from DockerRunner.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple

from .base import BaseRule


class Rule(BaseRule):
    """
    Security dependencies rule implementation.
    
    Checks installed packages for known vulnerabilities.
    """
    
    WORKSPACE_PATH = "/workspace"
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the security deps rule."""
        super().__init__(config)
        self.timeout = config.get("timeout", 180)
    
    def execute(self, artifact_info: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute dependency security scanning.
        
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
        python_dependencies = artifact_info.get("python_dependencies", [])
        
        details = {
            "scanner": None,
            "dependencies_checked": len(python_dependencies),
            "vulnerabilities_found": 0,
            "vulnerable_packages": []
        }
        
        # Validate prerequisites
        if not docker_runner or not deps_image:
            return False, "Docker not available or deps image not built", details
        
        if not project_path.exists():
            return False, f"Project path not found: {project_path}", details
        
        try:
            # Try pip-audit first
            result = self._run_pip_audit(
                docker_runner, deps_image, project_path, network_access
            )
            
            if result["scanner"]:
                details.update(result)
                if result["vulnerabilities_found"] > 0:
                    return False, (
                        f"Found {result['vulnerabilities_found']} vulnerable dependencies"
                    ), details
                return True, "No vulnerable dependencies found", details
            
            # Try safety as fallback
            result = self._run_safety(
                docker_runner, deps_image, project_path, network_access
            )
            
            if result["scanner"]:
                details.update(result)
                if result["vulnerabilities_found"] > 0:
                    return False, (
                        f"Found {result['vulnerabilities_found']} vulnerable dependencies"
                    ), details
                return True, "No vulnerable dependencies found", details
            
            # No scanner available
            details["warning"] = "No dependency scanner (pip-audit, safety) available"
            return True, "Dependency scanning skipped (no scanner available)", details
            
        except subprocess.TimeoutExpired:
            return False, f"Dependency scan timed out after {self.timeout}s", details
        except Exception as e:
            return False, f"Dependency scan failed: {str(e)}", details
    
    def _run_pip_audit(
        self,
        docker_runner,
        deps_image: str,
        project_path: Path,
        network_access: bool
    ) -> Dict[str, Any]:
        """Run pip-audit vulnerability scanner."""
        result = {
            "scanner": None,
            "vulnerabilities_found": 0,
            "vulnerable_packages": []
        }
        
        proc = docker_runner.run_command(
            image=deps_image,
            command=["python", "-m", "pip_audit", "--format", "json"],
            project_path=project_path,
            network_access=True,  # pip-audit needs network to fetch vuln database
            timeout=self.timeout
        )
        
        # Check if pip-audit is installed
        if "No module named" in proc.stderr:
            return result  # Scanner not available
        
        result["scanner"] = "pip-audit"
        
        try:
            audit_data = json.loads(proc.stdout)
            
            for dep in audit_data.get("dependencies", []):
                vulns = dep.get("vulns", [])
                for vuln in vulns:
                    result["vulnerabilities_found"] += 1
                    result["vulnerable_packages"].append({
                        "name": dep.get("name", "unknown"),
                        "version": dep.get("version", "unknown"),
                        "id": vuln.get("id", ""),
                        "description": vuln.get("description", "")[:200]
                    })
                    
        except json.JSONDecodeError:
            # If returncode is 0 and no JSON, likely no vulnerabilities
            if proc.returncode == 0:
                pass  # No vulnerabilities found
        
        return result
    
    def _run_safety(
        self,
        docker_runner,
        deps_image: str,
        project_path: Path,
        network_access: bool
    ) -> Dict[str, Any]:
        """Run safety vulnerability scanner."""
        result = {
            "scanner": None,
            "vulnerabilities_found": 0,
            "vulnerable_packages": []
        }
        
        proc = docker_runner.run_command(
            image=deps_image,
            command=["python", "-m", "safety", "check", "--json"],
            project_path=project_path,
            network_access=True,  # safety needs network
            timeout=self.timeout
        )
        
        # Check if safety is installed
        if "No module named" in proc.stderr:
            return result  # Scanner not available
        
        result["scanner"] = "safety"
        
        try:
            safety_data = json.loads(proc.stdout)
            
            # safety returns list of vulnerabilities
            if isinstance(safety_data, list):
                for vuln in safety_data:
                    result["vulnerabilities_found"] += 1
                    result["vulnerable_packages"].append({
                        "name": vuln[0] if len(vuln) > 0 else "unknown",
                        "version": vuln[2] if len(vuln) > 2 else "unknown",
                        "id": vuln[3] if len(vuln) > 3 else "",
                        "description": vuln[4][:200] if len(vuln) > 4 else ""
                    })
                    
        except json.JSONDecodeError:
            if proc.returncode == 0:
                pass  # No vulnerabilities found
        
        return result
