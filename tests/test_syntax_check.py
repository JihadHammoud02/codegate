"""
Tests for syntax check rule.
"""

import pytest
from pathlib import Path
import tempfile

from codegate.rules.syntax_check import Rule


def test_valid_syntax():
    """Test file with valid syntax."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "valid.py"
        test_file.write_text("""
def hello():
    print("Hello, world!")

if __name__ == "__main__":
    hello()
""")
        
        rule = Rule({})
        passed, message, details = rule.execute({
            "type": "python-script",
            "path": str(test_file)
        })
        
        assert passed is True
        assert "valid syntax" in message.lower()


def test_invalid_syntax():
    """Test file with invalid syntax."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "invalid.py"
        test_file.write_text("""
def hello()
    print("Missing colon")
""")
        
        rule = Rule({})
        passed, message, details = rule.execute({
            "type": "python-script",
            "path": str(test_file)
        })
        
        assert passed is False
        assert "syntax error" in message.lower()
        assert len(details.get("errors", [])) > 0


def test_multiple_files():
    """Test multiple Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir)
        
        (src_dir / "file1.py").write_text("print('File 1')\n")
        (src_dir / "file2.py").write_text("print('File 2')\n")
        
        rule = Rule({})
        passed, message, details = rule.execute({
            "type": "python-package",
            "path": str(src_dir)
        })
        
        assert passed is True
        assert details["files_checked"] == 2
