"""
Build/Import rule - validates that code can be imported/built successfully.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from .base import RuleExecutor


class BuildImportRule(RuleExecutor):
    """Rule to validate code can be imported or built."""
    
    def execute(self, config: Dict[str, Any], base_path: Path, artifacts_dir: Path) -> Dict[str, Any]:
        """Execute build/import validation.
        
        Args:
            config: Rule configuration (e.g., {'command': 'python -m py_compile file.py'})
            base_path: Base path for resolving relative paths
            artifacts_dir: Directory to store artifacts
            
        Returns:
            Result dict with status and message
        """
        command = config.get('command')
        if not command:
            return {
                'status': 'ERROR',
                'message': 'No command specified for build_import rule'
            }
        
        try:
            # Execute the build/import command
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(base_path),
                capture_output=True,
                text=True,
                timeout=60
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
                    'message': 'Build/import succeeded'
                }
            else:
                return {
                    'status': 'FAIL',
                    'message': f'Build/import failed with exit code {result.returncode}',
                    'stderr': result.stderr[:500]  # Truncate for summary
                }
                
        except subprocess.TimeoutExpired:
            return {
                'status': 'ERROR',
                'message': 'Build/import command timed out after 60 seconds'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Build/import execution error: {str(e)}'
            }
