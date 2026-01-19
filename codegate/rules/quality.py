"""
Quality rule - validates code quality metrics.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any

from .base import RuleExecutor


class QualityRule(RuleExecutor):
    """Rule to validate code quality."""
    
    def execute(self, config: Dict[str, Any], base_path: Path, artifacts_dir: Path) -> Dict[str, Any]:
        """Execute quality validation.
        
        Args:
            config: Rule configuration (e.g., {'command': 'pylint src/'})
            base_path: Base path for resolving relative paths
            artifacts_dir: Directory to store artifacts
            
        Returns:
            Result dict with status and message
        """
        command = config.get('command')
        if not command:
            return {
                'status': 'ERROR',
                'message': 'No command specified for quality rule'
            }
        
        try:
            # Execute the quality command
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(base_path),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Save output to artifacts
            output_file = artifacts_dir / 'output.txt'
            with open(output_file, 'w') as f:
                f.write(f"Command: {command}\n")
                f.write(f"Exit code: {result.returncode}\n\n")
                f.write(f"STDOUT:\n{result.stdout}\n\n")
                f.write(f"STDERR:\n{result.stderr}\n")
            
            # Allow configuration to specify acceptable exit codes
            # Many linters return non-zero for warnings, so be flexible
            acceptable_codes = config.get('acceptable_exit_codes', [0])
            
            if result.returncode in acceptable_codes:
                return {
                    'status': 'PASS',
                    'message': 'Quality checks passed'
                }
            else:
                return {
                    'status': 'FAIL',
                    'message': f'Quality checks failed (exit code {result.returncode})',
                    'output': result.stdout[:500]  # Truncate for summary
                }
                
        except subprocess.TimeoutExpired:
            return {
                'status': 'ERROR',
                'message': 'Quality check timed out after 2 minutes'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Quality check error: {str(e)}'
            }
