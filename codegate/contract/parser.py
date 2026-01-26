"""
YAML contract parser with schema validation.
"""

from pathlib import Path
from typing import Dict, Any
import yaml

from .schema import ContractSchema


class ContractParser:
    """Parser for CodeGate contract YAML files."""
    
    def __init__(self):
        """Initialize the contract parser."""
        self.schema = ContractSchema()
    
    def parse(self, contract_path: Path) -> Dict[str, Any]:
        """
        Parse and validate a contract YAML file.
        
        Args:
            contract_path: Path to the contract YAML file
        
        Returns:
            Parsed and validated contract dictionary
        
        Raises:
            ValueError: If the contract is invalid
            FileNotFoundError: If the contract file doesn't exist
        """
        if not contract_path.exists():
            raise FileNotFoundError(f"Contract file not found: {contract_path}")
        
        # Load YAML
        with open(contract_path, 'r') as f:
            try:
                contract_data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML syntax: {e}")
        
        if contract_data is None:
            raise ValueError("Contract file is empty")
        
        # Validate schema
        self.schema.validate(contract_data)
        
        # Resolve relative paths in the contract
        self._resolve_paths(contract_data, contract_path.parent)
        
        return contract_data
    
    def _resolve_paths(self, contract: Dict[str, Any], base_path: Path) -> None:
        """
        Resolve relative paths in the contract to absolute paths.
        
        Args:
            contract: Contract dictionary
            base_path: Base path for resolving relative paths
        """
        # Resolve project path
        if "project" in contract:
            project = contract["project"]
            if "path" in project:
                project_path = Path(project["path"])
                if not project_path.is_absolute():
                    project["path"] = str((base_path / project_path).resolve())
        
        # Resolve rule-specific paths
        if "rules" in contract:
            for rule_name, rule_config in contract["rules"].items():
                if isinstance(rule_config, dict):
                    # Resolve test_directory for unit_tests rule
                    if rule_name == "unit_tests" and "test_directory" in rule_config:
                        test_dir = Path(rule_config["test_directory"])
                        if not test_dir.is_absolute():
                            rule_config["test_directory"] = str((base_path / test_dir).resolve())

