"""
Contract loading and validation.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_contract(contract_file: str) -> Dict[str, Any]:
    """Load and validate a YAML contract file.
    
    Args:
        contract_file: Path to the YAML contract file
        
    Returns:
        Dict containing the contract configuration
        
    Raises:
        ValueError: If contract is invalid
        FileNotFoundError: If contract file doesn't exist
    """
    contract_path = Path(contract_file)
    
    if not contract_path.exists():
        raise FileNotFoundError(f"Contract file not found: {contract_file}")
    
    with open(contract_path, 'r') as f:
        contract = yaml.safe_load(f)
    
    if not contract:
        raise ValueError("Contract file is empty")
    
    # Validate basic structure
    if 'rules' not in contract:
        raise ValueError("Contract must contain 'rules' section")
    
    return contract
