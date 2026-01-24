"""
Base rule class for all CodeGate rules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class BaseRule(ABC):
    """Base class for all evaluation rules."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the rule.
        
        Args:
            config: Rule configuration from contract
        """
        self.config = config
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    def execute(self, artifact_info: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Execute the rule evaluation.
        
        Args:
            artifact_info: Information about the artifact to evaluate
        
        Returns:
            Tuple of (passed, message, details)
            - passed: Whether the rule passed
            - message: Human-readable message
            - details: Additional details about the evaluation
        """
        pass
    
    def get_name(self) -> str:
        """Get the rule name."""
        return self.__class__.__name__
