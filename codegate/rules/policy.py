"""
Policy rule - enforce forbidden modules, packages, and APIs.
"""

import ast
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, List, Set

from .base import BaseRule


class Rule(BaseRule):
    """Policy rule implementation."""
    
    def execute(self, artifact_info: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute policy enforcement.
        
        Checks for:
        - Forbidden module imports
        - Forbidden package usage
        - Forbidden API calls
        
        This rule performs static AST analysis locally (no Docker needed).
        
        Args:
            artifact_info: Information about the artifact
        
        Returns:
            Tuple of (passed, message, details)
        """
        project_path = artifact_info.get("absolute_path") or artifact_info.get("project_path", "")
        
        forbidden_modules = self.config.get("forbidden_modules", [])
        forbidden_packages = self.config.get("forbidden_packages", [])
        forbidden_apis = self.config.get("forbidden_apis", [])
        
        details = {
            "forbidden_modules": forbidden_modules,
            "forbidden_packages": forbidden_packages,
            "forbidden_apis": forbidden_apis,
            "violations": [],
            "files_checked": 0
        }
        
        try:
            project_dir = Path(project_path)
            
            if not project_dir.exists():
                return False, f"Project path not found: {project_path}", details
            
            # Find all Python files
            python_files = list(project_dir.rglob("*.py"))
            details["files_checked"] = len(python_files)
            
            violations = []
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse the Python file
                    tree = ast.parse(content, filename=str(py_file))
                    
                    # Check for forbidden imports
                    file_violations = self._check_imports(
                        tree, py_file, forbidden_modules, forbidden_packages
                    )
                    violations.extend(file_violations)
                    
                    # Check for forbidden API calls
                    api_violations = self._check_api_calls(
                        tree, py_file, forbidden_apis
                    )
                    violations.extend(api_violations)
                    
                except SyntaxError as e:
                    # Skip files with syntax errors (will be caught by syntax check)
                    continue
                except Exception as e:
                    # Skip files that can't be parsed
                    continue

            details["violations"] = violations

            if len(violations) > 0:
                return False, f"Found {len(violations)} policy violation(s)", details
            
            return True, "No policy violations found", details
            
        except Exception as e:
            return False, f"Policy check failed: {str(e)}", details
    
    def _check_imports(
        self, 
        tree: ast.AST, 
        file_path: Path, 
        forbidden_modules: List[str],
        forbidden_packages: List[str]
    ) -> List[Dict[str, Any]]:
        """Check for forbidden imports."""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    
                    # Check against forbidden modules
                    if module_name in forbidden_modules:
                        violations.append({
                            "type": "forbidden_module",
                            "file": str(file_path),
                            "line": node.lineno,
                            "module": module_name,
                            "message": f"Forbidden module '{module_name}' imported"
                        })
                    
                    # Check against forbidden packages (top-level package)
                    package = module_name.split('.')[0]
                    if package in forbidden_packages:
                        violations.append({
                            "type": "forbidden_package",
                            "file": str(file_path),
                            "line": node.lineno,
                            "package": package,
                            "message": f"Forbidden package '{package}' imported"
                        })
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    
                    # Check against forbidden modules
                    if module_name in forbidden_modules:
                        violations.append({
                            "type": "forbidden_module",
                            "file": str(file_path),
                            "line": node.lineno,
                            "module": module_name,
                            "message": f"Forbidden module '{module_name}' imported"
                        })
                    
                    # Check against forbidden packages
                    package = module_name.split('.')[0]
                    if package in forbidden_packages:
                        violations.append({
                            "type": "forbidden_package",
                            "file": str(file_path),
                            "line": node.lineno,
                            "package": package,
                            "message": f"Forbidden package '{package}' imported"
                        })
        
        return violations
    
    def _check_api_calls(
        self, 
        tree: ast.AST, 
        file_path: Path, 
        forbidden_apis: List[str]
    ) -> List[Dict[str, Any]]:
        """Check for forbidden API calls."""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Get the full call name
                call_name = self._get_call_name(node.func)
                
                if call_name in forbidden_apis:
                    violations.append({
                        "type": "forbidden_api",
                        "file": str(file_path),
                        "line": node.lineno,
                        "api": call_name,
                        "message": f"Forbidden API '{call_name}' called"
                    })
        
        return violations
    
    def _get_call_name(self, node: ast.AST) -> str:
        """Get the full name of a function call."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_call_name(node.value)
            return f"{value}.{node.attr}"
        else:
            return ""
