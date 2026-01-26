"""
Tests for contract parser.
"""

import pytest
from pathlib import Path
import tempfile

from codegate.contract.parser import ContractParser


def test_parse_valid_contract():
    """Test parsing a valid contract."""
    contract_yaml = """
Environment:
    runtime_image: python:3.11-slim

project:
    path: ./src
    entry_point: main.py

rules:
    build_imports:
        enabled: true
    unit_tests:
        enabled: false
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(contract_yaml)
        contract_path = Path(f.name)
    
    try:
        parser = ContractParser()
        contract = parser.parse(contract_path)
        
        assert contract["Environment"]["runtime_image"] == "python:3.11-slim"
        assert contract["project"]["path"].endswith("/src")
        assert contract["project"]["entry_point"] == "main.py"
        assert "build_imports" in contract["rules"]
        assert contract["rules"]["build_imports"]["enabled"] is True
    finally:
        contract_path.unlink()


def test_parse_missing_required_field():
    """Test parsing contract with missing required field."""
    contract_yaml = """
Environment:
    runtime_image: python:3.11-slim

project:
    path: ./src
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(contract_yaml)
        contract_path = Path(f.name)
    
    try:
        parser = ContractParser()
        with pytest.raises(ValueError, match="Missing required field: rules"):
            parser.parse(contract_path)
    finally:
        contract_path.unlink()


def test_parse_invalid_yaml():
    """Test parsing invalid YAML."""
    contract_yaml = """
project:
  name: test-project
  invalid: [unclosed
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(contract_yaml)
        contract_path = Path(f.name)
    
    try:
        parser = ContractParser()
        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            parser.parse(contract_path)
    finally:
        contract_path.unlink()


def test_parse_nonexistent_file():
    """Test parsing non-existent file."""
    parser = ContractParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("/nonexistent/contract.yaml"))
