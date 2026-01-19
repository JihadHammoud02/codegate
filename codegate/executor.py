"""
Contract executor - runs rules and collects results.
"""

import json
from pathlib import Path
from typing import Dict, Any

from .rules import get_rule_executor


def execute_contract(contract: Dict[str, Any], base_path: Path) -> Dict[str, Dict[str, Any]]:
    """Execute all rules defined in the contract.
    
    Args:
        contract: The loaded contract configuration
        base_path: Base path for resolving relative paths in contract
        
    Returns:
        Dict mapping rule names to their execution results
    """
    results = {}
    artifacts_dir = Path('.artifacts')
    
    rules = contract.get('rules', {})
    
    for rule_name, rule_config in rules.items():
        # Get the rule executor
        executor = get_rule_executor(rule_name)
        
        if executor is None:
            results[rule_name] = {
                'status': 'ERROR',
                'message': f'Unknown rule: {rule_name}'
            }
            continue
        
        # Create artifacts directory for this rule
        rule_artifacts_dir = artifacts_dir / rule_name
        rule_artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Execute the rule
        try:
            result = executor.execute(rule_config, base_path, rule_artifacts_dir)
            results[rule_name] = result
            
            # Save artifacts
            artifact_file = rule_artifacts_dir / 'result.json'
            with open(artifact_file, 'w') as f:
                json.dump(result, f, indent=2)
                
        except Exception as e:
            error_result = {
                'status': 'ERROR',
                'message': str(e)
            }
            results[rule_name] = error_result
            
            # Save error artifacts
            artifact_file = rule_artifacts_dir / 'result.json'
            with open(artifact_file, 'w') as f:
                json.dump(error_result, f, indent=2)
    
    return results
