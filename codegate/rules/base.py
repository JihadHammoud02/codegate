"""
Base class for rule executors.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


class RuleExecutor(ABC):
    """Base class for all rule executors."""
    
    @abstractmethod
    def execute(self, config: Dict[str, Any], base_path: Path, artifacts_dir: Path) -> Dict[str, Any]:
        """Execute the rule.
        
        Args:
            config: Rule configuration from the contract
            base_path: Base path for resolving relative paths
            artifacts_dir: Directory to store rule artifacts
            
        Returns:
            Dict with at least 'status' key (PASS/FAIL/ERROR) and optional 'message' and other metadata
        """
        pass
