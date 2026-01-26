"""Unit tests for the ContractSchema validation logic.

We cover common error branches to lift coverage in `codegate.contract.schema`.
"""

from __future__ import annotations

import pytest

from codegate.contract.schema import ContractSchema


def test_schema_rejects_non_dict_contract():
    schema = ContractSchema()
    with pytest.raises(ValueError, match="Contract must be a dictionary"):
        schema.validate("nope")  # type: ignore[arg-type]


def test_schema_requires_environment_project_rules():
    schema = ContractSchema()
    with pytest.raises(ValueError, match="Missing required field: Environment"):
        schema.validate({"project": {}, "rules": {}})

    with pytest.raises(ValueError, match="Missing required field: project"):
        schema.validate({"Environment": {}, "rules": {}})

    with pytest.raises(ValueError, match="Missing required field: rules"):
        schema.validate({"Environment": {}, "project": {}})


def test_schema_environment_runtime_image_required():
    schema = ContractSchema()
    with pytest.raises(ValueError, match="runtime_image"):
        schema.validate({"Environment": {}, "project": {"path": "."}, "rules": {}})


def test_schema_environment_type_checks():
    schema = ContractSchema()

    # network_access must be bool
    with pytest.raises(ValueError, match="Environment.network_access"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim", "network_access": "yes"},
                "project": {"path": "."},
                "rules": {},
            }
        )

    # system_dependencies must be list
    with pytest.raises(ValueError, match="Environment.system_dependencies"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim", "system_dependencies": "git"},
                "project": {"path": "."},
                "rules": {},
            }
        )


def test_schema_project_section_checks():
    schema = ContractSchema()

    with pytest.raises(ValueError, match="'project' must have a 'path'"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim"},
                "project": {},
                "rules": {},
            }
        )

    with pytest.raises(ValueError, match="project.entry_point"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim"},
                "project": {"path": ".", "entry_point": 123},
                "rules": {},
            }
        )

    with pytest.raises(ValueError, match="project.python_dependencies"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim"},
                "project": {"path": ".", "python_dependencies": "requests"},
                "rules": {},
            }
        )


def test_schema_rules_section_checks_and_unknown_rule_warns():
    schema = ContractSchema()

    # rules must be dict
    with pytest.raises(ValueError, match="'rules' must be a dictionary"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim"},
                "project": {"path": "."},
                "rules": [],
            }
        )

    # unknown rules should warn but not error
    with pytest.warns(UserWarning):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim"},
                "project": {"path": "."},
                "rules": {"custom_rule": {"enabled": True}},
            }
        )

    # rule config must be dict
    with pytest.raises(ValueError, match="config must be a dictionary"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim"},
                "project": {"path": "."},
                "rules": {"policy": True},
            }
        )

    # enabled required
    with pytest.raises(ValueError, match="must have an 'enabled'"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim"},
                "project": {"path": "."},
                "rules": {"policy": {}},
            }
        )

    # enabled must be bool
    with pytest.raises(ValueError, match="enabled.*boolean"):
        schema.validate(
            {
                "Environment": {"runtime_image": "python:3.11-slim"},
                "project": {"path": "."},
                "rules": {"policy": {"enabled": "yes"}},
            }
        )
