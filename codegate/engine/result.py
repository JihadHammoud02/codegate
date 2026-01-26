"""
Result classes for evaluation outcomes.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class RuleResult:
    """Result of a single rule evaluation."""
    
    rule_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule": self.rule_name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "duration": round(self.duration, 3)
        }


@dataclass
class EvaluationResult:
    """Result of a complete contract evaluation."""
    
    project_name: str
    artifact_type: str
    artifact_path: str
    rule_results: List[RuleResult]
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        passed_count = sum(1 for r in self.rule_results if r.passed)
        failed_count = len(self.rule_results) - passed_count
        
        return {
            "project": self.project_name,
            "artifact": {
                "type": self.artifact_type,
                "path": self.artifact_path
            },
            "summary": {
                "total": len(self.rule_results),
                "passed": passed_count,
                "failed": failed_count,
                "success_rate": round(passed_count / len(self.rule_results) * 100, 1) if self.rule_results else 0.0,
                "duration": round(self.duration, 3)
            },
            "results": [r.to_dict() for r in self.rule_results]
        }
