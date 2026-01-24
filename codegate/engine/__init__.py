"""
Engine module - Rule runner and result aggregation.
"""

from .runner import EvaluationRunner
from .result import RuleResult, EvaluationResult

__all__ = ["EvaluationRunner", "RuleResult", "EvaluationResult"]
