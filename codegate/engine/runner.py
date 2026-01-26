"""
Evaluation runner - orchestrates rule execution and result aggregation.

This module is the main orchestrator that:
1. Parses contract configuration
2. Builds Docker deps image via DockerRunner
3. Executes each rule inside the Docker container
4. Aggregates and returns results
"""

import time
from pathlib import Path
from typing import Dict, Any, List
import importlib
import subprocess

from .result import RuleResult, EvaluationResult
from .docker_runner import DockerRunner


class EvaluationRunner:
    """
    Runner for executing contract evaluations.
    
    Flow:
    1. Extract config from contract (runtime_image, system_deps, python_deps)
    2. Build deps image with all dependencies (via DockerRunner)
    3. For each enabled rule:
       - Execute rule logic inside container with deps image
    4. Aggregate and return results
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the evaluation runner.
        
        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.docker_runner = DockerRunner(verbose=verbose)
        self._deps_image = None
    
    def run(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all rules defined in the contract.
        
        Args:
            contract: Parsed contract dictionary
        
        Returns:
            Evaluation results dictionary
        """
        start_time = time.time()
        
        if self.verbose:
            print("\n" + "="*60)
            print("Starting CodeGate Contract Evaluation")
            print("="*60 + "\n")
        
        # Extract contract components
        environment = contract.get("Environment", {})
        project = contract.get("project", {})
        rules = contract.get("rules", {})
        
        # Step 1: Build artifact info and deps image
        artifact_info = self._prepare_environment(environment, project)
        
        # Step 2: Run each enabled rule
        rule_results: List[RuleResult] = []
        
        for rule_name, rule_config in rules.items():
            # Skip disabled rules
            if isinstance(rule_config, dict) and not rule_config.get("enabled", True):
                if self.verbose:
                    print(f"[SKIP] {rule_name} (disabled)")
                continue
            
            if self.verbose:
                print(f"\n[RULE] {rule_name}")
                print("-" * 40)
            
            # Run the rule
            result = self._run_rule(rule_name, rule_config, artifact_info)
            rule_results.append(result)
            
            if self.verbose:
                status = "✓ PASSED" if result.passed else "✗ FAILED"
                print(f"  Result: {status}")
                print(f"  Message: {result.message}")
        
        # Step 3: Aggregate results
        evaluation_result = EvaluationResult(
            project_name=project.get("entry_point", "project"),
            artifact_type="docker-container",
            artifact_path=project.get("path", ""),
            rule_results=rule_results,
            duration=time.time() - start_time
        )
        
        if self.verbose:
            print("\n" + "="*60)
            print(f"Evaluation Complete ({evaluation_result.duration:.2f}s)")
            print("="*60 + "\n")
        
        return evaluation_result.to_dict()
    
    def _prepare_environment(
        self, 
        environment: Dict[str, Any], 
        project: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare the Docker environment for evaluation.
        
        This method:
        1. Extracts all config from contract YAML
        2. Builds Docker deps image with system + Python dependencies
        3. Returns artifact_info dict for rules to use
        
        Args:
            environment: Environment section from contract
            project: Project section from contract
            
        Returns:
            artifact_info dictionary with all config + deps_image
        """
        # Extract project path
        project_path = Path(project.get("path", "."))
        if not project_path.is_absolute():
            project_path = Path.cwd() / project_path
        
        if not project_path.exists():
            raise ValueError(f"Project path not found: {project_path}")
        
        absolute_path = project_path.resolve()
        
        # Extract Environment config from YAML
        runtime_image = environment.get("runtime_image")
        network_access = environment.get("network_access", False)
        system_dependencies = environment.get("system_dependencies", [])
        
        # Extract Project config from YAML
        entry_point = project.get("entry_point", "")
        python_dependencies = project.get("python_dependencies", [])
        
        if self.verbose:
            print("Configuration from contract:")
            print(f"  Project path: {absolute_path}")
            print(f"  Runtime image: {runtime_image}")
            print(f"  Network access: {network_access}")
            print(f"  System deps: {system_dependencies}")
            print(f"  Python deps: {python_dependencies}")
            print(f"  Entry point: {entry_point}")
        
        # Build deps image
        deps_image = None
        try:
            if self.verbose:
                print("\nBuilding Docker dependency image...")
            
            deps_image = self.docker_runner.build_deps_image(
                runtime_image=runtime_image,
                system_dependencies=system_dependencies,
                python_dependencies=python_dependencies,
                project_path=absolute_path
            )
            self._deps_image = deps_image
            
            if self.verbose:
                print(f"  Ready: {deps_image}\n")
                
        except Exception as e:
            if self.verbose:
                print(f"  Warning: Failed to build deps image: {e}")
                print("  Rules will attempt local execution.\n")
        
        # Build artifact_info for rules
        artifact_info = {
            # Paths
            "project_path": str(project_path),
            "absolute_path": str(absolute_path),
            
            # Environment settings from contract
            "runtime_image": runtime_image,
            "network_access": network_access,
            "system_dependencies": system_dependencies,
            
            # Project settings from contract
            "entry_point": entry_point,
            "python_dependencies": python_dependencies,
            
            # Docker resources
            "docker_runner": self.docker_runner,
            "deps_image": deps_image,
        }
        
        return artifact_info
    
    def _run_rule(
        self,
        rule_name: str,
        rule_config: Any,
        artifact_info: Dict[str, Any]
    ) -> RuleResult:
        """
        Run a single rule.
        
        The rule's execute() method receives artifact_info which contains:
        - docker_runner: DockerRunner instance
        - deps_image: Pre-built image with all dependencies
        - network_access: Sandbox setting
        - project_path, entry_point, etc.
        
        The rule can use docker_runner.run_command() to execute
        commands inside the container.
        
        Args:
            rule_name: Name of the rule (e.g., 'build_imports')
            rule_config: Rule configuration from contract
            artifact_info: Environment and Docker info
        
        Returns:
            RuleResult with pass/fail status
        """
        start_time = time.time()
        
        try:
            # Load rule module dynamically
            rule_module = self._load_rule_module(rule_name)
            
            # Get rule config (merge with defaults)
            config = rule_config if isinstance(rule_config, dict) else {}
            
            # Instantiate and execute rule
            rule_instance = rule_module.Rule(config)
            passed, message, details = rule_instance.execute(artifact_info)
            
            return RuleResult(
                rule_name=rule_name,
                passed=passed,
                message=message,
                details=details,
                duration=time.time() - start_time
            )
            
        except Exception as e:
            if self.verbose:
                import traceback
                traceback.print_exc()
            
            return RuleResult(
                rule_name=rule_name,
                passed=False,
                message=f"Rule execution failed: {str(e)}",
                details={"error": str(e)},
                duration=time.time() - start_time
            )
    
    def _load_rule_module(self, rule_name: str):
        """
        Load a rule module dynamically.
        
        Args:
            rule_name: Name of the rule (e.g., 'build_imports', 'unit_tests')
        
        Returns:
            Loaded rule module with Rule class
        """
        # Convert rule name to module name
        module_name = rule_name.replace("-", "_")
        module_path = f"codegate.rules.{module_name}"
        
        try:
            return importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Rule '{rule_name}' not found at {module_path}: {e}")
