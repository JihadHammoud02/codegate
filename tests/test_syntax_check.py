"""Legacy tests for a removed rule.

The original project had a `syntax_check` rule. It was removed in favor of the
contract-driven rules shipped today (build_imports, unit_tests, security_*,
policy).
"""

import pytest


pytest.skip("Legacy syntax_check rule removed", allow_module_level=True)
