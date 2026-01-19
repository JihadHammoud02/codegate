"""
Unit tests rule - runs unit tests and validates they pass.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any

from .base import RuleExecutor


class UnitTestsRule(RuleExecutor):
    """Rule to run and validate unit tests."""
    
    def execute(self, config: Dict[str, Any], base_path: Path, artifacts_dir: Path) -> Dict[str, Any]:
        """Execute unit tests.
        
        Args:
            config: Rule configuration (e.g., {'command': 'pytest tests/'})
            base_path: Base path for resolving relative paths
            artifacts_dir: Directory to store artifacts
            
        Returns:
            Result dict with status and message
        """
        command = config.get('command')
        if not command:
            return {
                'status': 'ERROR',
                'message': 'No command specified for unit_tests rule'
            }
        
        try:
            # Execute the test command
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(base_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for tests
            )
            
            # Save output to artifacts
            output_file = artifacts_dir / 'output.txt'
            with open(output_file, 'w') as f:
                f.write(f"Command: {command}\n")
                f.write(f"Exit code: {result.returncode}\n\n")
                f.write(f"STDOUT:\n{result.stdout}\n\n")
                f.write(f"STDERR:\n{result.stderr}\n")
            
            if result.returncode == 0:
                return {
                    'status': 'PASS',
                    'message': 'All tests passed'
                }
            else:
                return {
                    'status': 'FAIL',
                    'message': f'Tests failed with exit code {result.returncode}',
                    'stderr': result.stderr[:500]  # Truncate for summary
                }
                
        except subprocess.TimeoutExpired:
            return {
                'status': 'ERROR',
                'message': 'Tests timed out after 5 minutes'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Test execution error: {str(e)}'
            }
