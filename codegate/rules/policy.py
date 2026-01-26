"""Policy rule - enforce forbidden packages and APIs.

Policy focuses on *static* checks that don't require Docker:

- Forbidden *packages* (distribution names, i.e. what you `pip install`)
- Forbidden API calls (e.g. `eval`, `pickle.loads`)

Important: Users specify forbidden packages using the **distribution name**.
We do not compare against import top-level module names.
"""

import ast
import importlib.metadata
from pathlib import Path
from typing import Dict, Any, Tuple, List, Set

from .base import BaseRule


class Rule(BaseRule):
    """Policy rule implementation."""
    
    def execute(self, artifact_info: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute policy enforcement.
        
        Checks for:
        - Forbidden package usage (distribution names)
        - Forbidden API calls
        
        This rule performs static AST analysis locally (no Docker needed).
        
        Args:
            artifact_info: Information about the artifact
        
        Returns:
            Tuple of (passed, message, details)
        """
        project_path = artifact_info.get("absolute_path") or artifact_info.get("project_path", "")
        project_dir = Path(project_path)

        # Users provide distribution names (what you `pip install`).
        forbidden_packages: Set[str] = {
            p for p in self.config.get("forbidden_packages", []) if isinstance(p, str) and p.strip()
        }
        forbidden_apis = self.config.get("forbidden_apis", [])

        pkg_map = importlib.metadata.packages_distributions()

        used_distributions: Set[str] = set()
        
        details = {
            "forbidden_packages": sorted(forbidden_packages),
            "forbidden_apis": forbidden_apis,
            "used_distributions": [],
            "violations": [],
            "files_checked": 0
        }
        
        try:
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
                    file_violations = self._check_imports(tree, py_file, forbidden_packages, used_distributions, pkg_map)
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
            details["used_distributions"] = sorted(used_distributions)

            if len(violations) > 0:
                return False, f"Found {len(violations)} policy violation(s)", details
            
            return True, "No policy violations found", details
            
        except Exception as e:
            return False, f"Policy check failed: {str(e)}", details

    def _top_level_import_to_distributions(self, pkg_map: Dict[str, List[str]], module_name: str) -> List[str]:
        """Map an import name to *all* candidate distribution names.

        importlib.metadata.packages_distributions() is many-to-many, so we do NOT
        pick [0]. We return the full candidate list.
        """
        top_level = module_name.split(".")[0]
        try:
            return list(pkg_map.get(top_level) or [])
        except Exception:
            return []
    
   def _check_imports(
    self,
    tree: ast.AST,
    file_path: Path,
    forbidden_packages: Set[str],
    used_distributions: Set[str],
    pkg_map: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """Collect used distributions and emit per-import violations.
    forbidden_packages are distribution names (pip install names).
    """
    violations: List[Dict[str, Any]] = []
    cache: dict[str, Set[str]] = {}  # optional per-file cache

    def resolve_candidates(module_name: str) -> Set[str]:
        top = module_name.split(".")[0]
        if top not in cache:
            cache[top] = set(self._top_level_import_to_distributions(pkg_map,top))
        return cache[top]

    def add_violation(line: int, module_name: str, forbidden: str) -> None:
        violations.append({
            "type": "forbidden_package",
            "file": str(file_path),
            "line": line,
            "package": forbidden,
            "import": module_name,
            "message": f"Forbidden dependency '{forbidden}' is used (imported via '{module_name}')",
        })

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                candidates = resolve_candidates(module_name)
                used_distributions.update(candidates)

                hits = candidates & forbidden_packages
                for forbidden in hits:
                    add_violation(node.lineno, module_name, forbidden)

        elif isinstance(node, ast.ImportFrom) and node.module:
            module_name = node.module
            candidates = resolve_candidates(module_name)
            used_distributions.update(candidates)

            hits = candidates & forbidden_packages
            for forbidden in hits:
                add_violation(node.lineno, module_name, forbidden)

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
