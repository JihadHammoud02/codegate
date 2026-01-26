"""
Contract schema validation.
"""

from typing import Dict, Any, List


class ContractSchema:
    """Schema validator for CodeGate contracts."""
    
    def __init__(self):
        """Initialize the schema validator."""
        self.required_fields = ["Environment", "project", "rules"]
    
    def validate(self, contract: Dict[str, Any]) -> None:
        """
        Validate a contract against the schema.
        
        Args:
            contract: Contract dictionary to validate
        
        Raises:
            ValueError: If the contract is invalid
        """
        if not isinstance(contract, dict):
            raise ValueError("Contract must be a dictionary")
        
        # Check required fields
        for field in self.required_fields:
            if field not in contract:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate Environment section
        self._validate_environment(contract["Environment"])
        
        # Validate project section
        self._validate_project(contract["project"])
        
        # Validate rules section
        self._validate_rules(contract["rules"])
    
    def _validate_environment(self, environment: Any) -> None:
        """Validate the Environment section."""
        if not isinstance(environment, dict):
            raise ValueError("'Environment' must be a dictionary")
        
        if "runtime_image" not in environment:
            raise ValueError("'Environment' must have a 'runtime_image' field")
        
        # Validate optional fields
        if "network_access" in environment and not isinstance(environment["network_access"], bool):
            raise ValueError("'Environment.network_access' must be a boolean")
        
        if "system_dependencies" in environment and not isinstance(environment["system_dependencies"], list):
                raise ValueError("'Environment.system_dependencies' must be a list")
    
    def _validate_project(self, project: Any) -> None:
        """Validate the project section."""
        if not isinstance(project, dict):
            raise ValueError("'project' must be a dictionary")
        
        if "path" not in project:
            raise ValueError("'project' must have a 'path' field")

        if "entry_point" not in project:
            raise ValueError("'project' must have an 'entry_point' field")

        if "entry_point" not isinstance(project["entry_point"], str):
            raise ValueError("'project.entry_point' must be a string")
        
        # Validate optional fields
        if "python_dependencies" in project:
            if not isinstance(project["python_dependencies"], list):
                raise ValueError("'project.python_dependencies' must be a list")
    
    def _validate_rules(self, rules: Any) -> None:
        """Validate the rules section."""
        if not isinstance(rules, dict):
            raise ValueError("'rules' must be a dictionary")
        
        # Don't Allow empty rules section - user can choose to run no rules
        if len(rules) == 0:
            raise ValueError("'rules' section cannot be empty")
        
        # Valid rule names - these are the available built-in rules
        valid_rules = {
            "build_imports", "unit_tests", "security_sast", 
            "security_deps", "policy"
        }
        
        # Validate each rule
        for rule_name, rule_config in rules.items():
            if not isinstance(rule_name, str):
                raise ValueError(f"Rule name must be a string: {rule_name}")
            
            # Warn about unknown rules but don't fail - allows for custom rules
            if rule_name not in valid_rules:
                import warnings
                warnings.warn(
                    f"Unknown rule '{rule_name}'. Valid built-in rules are: {', '.join(sorted(valid_rules))}. "
                    UserWarning
                )
            
            # Rule config must be a dict with enabled field
            if not isinstance(rule_config, dict):
                raise ValueError(
                    f"Rule '{rule_name}' config must be a dictionary"
                )
            
            if "enabled" not in rule_config:
                raise ValueError(f"Rule '{rule_name}' must have an 'enabled' field")
            
            if not isinstance(rule_config["enabled"], bool):
                raise ValueError(f"Rule '{rule_name}' 'enabled' must be a boolean")
            
            # Validate rule-specific fields only for known rules
            if rule_name in valid_rules:
                self._validate_rule_specific(rule_name, rule_config)
    
    def _validate_rule_specific(self, rule_name: str, rule_config: Dict[str, Any]) -> None:
        """Validate rule-specific configuration fields."""
        if rule_name == "build_imports":
            if "import_timeout" in rule_config:
                if not isinstance(rule_config["import_timeout"], int):
                    raise ValueError("'build_imports.import_timeout' must be an integer")
        
        elif rule_name == "unit_tests":
            if "test_directory" not in rule_config:
                raise ValueError("'unit_tests' must have a 'test_directory' field")
            if not isinstance(rule_config["test_directory"], str):
                raise ValueError("'unit_tests.test_directory' must be a string")
            
            if "coverage_threshold" in rule_config:
                if not isinstance(rule_config["coverage_threshold"], (int, float)):
                    raise ValueError("'unit_tests.coverage_threshold' must be a number")
        
        elif rule_name == "policy":
            if "forbidden_packages" in rule_config:
                if not isinstance(rule_config["forbidden_packages"], list):
                    raise ValueError("'policy.forbidden_packages' must be a list")

                # Ensure list of strings (distribution names)
                for p in rule_config["forbidden_packages"]:
                    if not isinstance(p, str):
                        raise ValueError("'policy.forbidden_packages' must be a list of strings")
            
            if "forbidden_apis" in rule_config:
                if not isinstance(rule_config["forbidden_apis"], list):
                    raise ValueError("'policy.forbidden_apis' must be a list")

                for api in rule_config["forbidden_apis"]:
                    if not isinstance(api, str):
                        raise ValueError("'policy.forbidden_apis' must be a list of strings")

