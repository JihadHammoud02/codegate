"""
Rules module - contains all rule implementations.
"""

from .base import RuleExecutor
from .build_import import BuildImportRule
from .unit_tests import UnitTestsRule
from .security_sast import SecuritySASTRule
from .security_deps import SecurityDepsRule
from .policy import PolicyRule
from .quality import QualityRule


# Registry of available rules
RULE_REGISTRY = {
    'build_import': BuildImportRule,
    'unit_tests': UnitTestsRule,
    'security_sast': SecuritySASTRule,
    'security_deps': SecurityDepsRule,
    'policy': PolicyRule,
    'quality': QualityRule,
}


def get_rule_executor(rule_name: str) -> RuleExecutor:
    """Get a rule executor by name.
    
    Args:
        rule_name: Name of the rule
        
    Returns:
        RuleExecutor instance or None if rule not found
    """
    rule_class = RULE_REGISTRY.get(rule_name)
    if rule_class:
        return rule_class()
    return None
