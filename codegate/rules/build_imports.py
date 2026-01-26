"""
Build Imports Rule - Validate Python project can be built and imported.

This rule validates:
1. All Python files compile without syntax errors (compileall)
2. The entrypoint module can be imported without errors

Uses the pre-built deps_image from DockerRunner which already has:
- System dependencies installed
- Python dependencies installed
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple

from .base import BaseRule


class Rule(BaseRule):
    """
    Build imports rule implementation.
    
    Phases:
    - Phase 1: Compilation (python -m compileall)
    - Phase 2: Entrypoint Import (importlib.import_module)
    
    Uses deps_image from artifact_info (pre-built by runner).
    """
    
    WORKSPACE_PATH = "/workspace"
    EXCLUDE_DIRS = {"__pycache__", ".pytest_cache"}
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the build imports rule."""
        super().__init__(config)
        self.import_timeout = config.get("import_timeout", 120)
    
    def execute(self, artifact_info: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute build imports check.
        
        Args:
            artifact_info: Must contain:
                - docker_runner: DockerRunner instance
                - deps_image: Pre-built image with dependencies
                - absolute_path: Path to project
                - entry_point: Main module to import
                - network_access: Network access flag
                
        Returns:
            Tuple of (passed, message, details)
        """
        # Extract from artifact_info
        docker_runner = artifact_info.get("docker_runner")
        deps_image = artifact_info.get("deps_image")
        project_path = Path(artifact_info.get("absolute_path", ""))
        entry_point = artifact_info.get("entry_point", "")
        network_access = artifact_info.get("network_access", False)
        
        
        details = {
            "phases": {},
            "entry_point": entry_point,
            "import_timeout": self.import_timeout,
        }
        
        # Validate prerequisites
        
        if not project_path.exists():
            return False, f"Project path not found: {project_path}", details
        
        try:
            # Phase 1: Compile all Python files
            phase1 = self._phase_compile(
                docker_runner=docker_runner,
                deps_image=deps_image,
                project_path=project_path,
                network_access=network_access
            )
            details["phases"]["compilation"] = phase1
            
            if not phase1["success"]:
                return False, f"Compilation failed: {phase1['error']}", details
            
            # Phase 2: Import entrypoint module
            phase2 = self._phase_import(
                docker_runner=docker_runner,
                deps_image=deps_image,
                project_path=project_path,
                entry_point=entry_point,
                network_access=network_access
            )
            details["phases"]["entrypoint_import"] = phase2
            
            if not phase2["success"]:
                return False, f"Import failed: {phase2['error']}", details
            
            return True, "Build and import checks passed", details
            
        except subprocess.TimeoutExpired:
            return False, f"Timed out after {self.import_timeout}s", details
        except Exception as e:
            return False, f"Check failed: {str(e)}", details
    
    def _phase_compile(
        self,
        docker_runner,
        deps_image: str,
        project_path: Path,
        network_access: bool
    ) -> Dict[str, Any]:
        """
        Phase 1: Compile all Python files.
        
        Command: python -m compileall -q /workspace
        
        Catches: syntax errors, indentation errors, broken f-strings
        """
        result = {
            "success": False,
            "error": None,
            "files_compiled": 0,
        }
        
        try:
            # Exclude cache directories and allow writes for this step so compileall can
            # create __pycache__ files without failing on a read-only mount.
            exclude_re = r"(__pycache__|\\.pytest_cache)"
            proc = docker_runner.run_command(
                image=deps_image,
                command=[
                    "python",
                    "-m", "compileall",
                    "-q",
                    "-x", exclude_re,
                    self.WORKSPACE_PATH
                ],
                project_path=project_path,
                network_access=network_access,
                writable=True,
                timeout=self.import_timeout
            )
            
            if proc.returncode != 0:
                # Parse error message
                error_output = proc.stderr or proc.stdout
                result["error"] = self._parse_compile_error(error_output)
                result["stderr"] = proc.stderr
                result["stdout"] = proc.stdout
            else:
                result["success"] = True
                # Count only .py files outside cache directories
                result["files_compiled"] = sum(
                    1
                    for p in project_path.rglob("*.py")
                    if not any(part in self.EXCLUDE_DIRS for part in p.parts)
                )
                
        except subprocess.TimeoutExpired:
            result["error"] = f"Compilation timed out"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _phase_import(
        self,
        docker_runner,
        deps_image: str,
        project_path: Path,
        entry_point: str,
        network_access: bool
    ) -> Dict[str, Any]:
        """
        Phase 2: Import the entrypoint module.
        
        Command: python -c "import importlib; importlib.import_module('module')"
        
        Catches: missing modules, circular imports, unresolved dependencies
        """
        result = {
            "success": False,
            "error": None,
            "module_imported": None,
        }
        
        # Convert file path to module name
        # e.g., "src/app.py" -> "src.app"
        module_name = entry_point.replace(".py", "").replace("/", ".").replace("\\", ".")
        
        import_code = f"import importlib; importlib.import_module('{module_name}'); print('IMPORT_OK')"
        
        try:
            proc = docker_runner.run_command(
                image=deps_image,
                command=["python", "-c", import_code],
                project_path=project_path,
                network_access=network_access,
                timeout=self.import_timeout
            )
            
            if proc.returncode != 0 or "IMPORT_OK" not in proc.stdout:
                error_output = proc.stderr or proc.stdout
                result["error"] = self._parse_import_error(error_output, module_name)
                result["stderr"] = proc.stderr
                result["stdout"] = proc.stdout
            else:
                result["success"] = True
                result["module_imported"] = module_name
                
        except subprocess.TimeoutExpired:
            result["error"] = f"Import timed out"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _parse_compile_error(self, output: str) -> str:
        """Extract meaningful error from compilation output."""
        lines = output.strip().split('\n')
        return output[-300:] if len(output) > 300 else output
    
    def _parse_import_error(self, output: str, module_name: str) -> str:
        """Extract meaningful error from import output."""
        lines = output.strip().split('\n')
        return f"Failed to import '{module_name}'"
