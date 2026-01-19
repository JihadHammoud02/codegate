"""
Security SAST rule - performs static application security testing.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any

from .base import RuleExecutor


class SecuritySASTRule(RuleExecutor):
    """Rule to perform static application security testing."""
    
    def execute(self, config: Dict[str, Any], base_path: Path, artifacts_dir: Path) -> Dict[str, Any]:
        """Execute SAST scanning.
        
        Args:
            config: Rule configuration (e.g., {'command': 'bandit -r .'})
            base_path: Base path for resolving relative paths
            artifacts_dir: Directory to store artifacts
            
        Returns:
            Result dict with status and message
        """
        command = config.get('command')
        if not command:
            return {
                'status': 'ERROR',
                'message': 'No command specified for security_sast rule'
            }
        
        try:
            # Execute the SAST command
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
            
            # Different tools have different exit codes
            # Some return 0 for no issues, 1 for issues found
            # Allow configuration to specify acceptable exit codes
            acceptable_codes = config.get('acceptable_exit_codes', [0])
            
            if result.returncode in acceptable_codes:
                return {
                    'status': 'PASS',
                    'message': 'SAST scan completed with no critical issues'
                }
            else:
                return {
                    'status': 'FAIL',
                    'message': f'SAST scan found security issues (exit code {result.returncode})',
                    'output': result.stdout[:500]  # Truncate for summary
                }
                
        except subprocess.TimeoutExpired:
            return {
                'status': 'ERROR',
                'message': 'SAST scan timed out after 2 minutes'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'SAST execution error: {str(e)}'
            }
