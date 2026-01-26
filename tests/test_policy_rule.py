"""Focused unit tests for the policy rule.

Policy is local-only and is the easiest place to get meaningful coverage without
requiring Docker.
"""

from __future__ import annotations

from pathlib import Path

from codegate.rules.policy import Rule


def test_policy_passes_when_no_forbidden_apis(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("\n")
    (tmp_path / "pkg" / "mod.py").write_text("def add(a,b):\n    return a+b\n")

    rule = Rule({"forbidden_apis": ["eval"], "forbidden_packages": []})
    passed, message, details = rule.execute({"absolute_path": str(tmp_path)})

    assert passed is True
    assert details.get("violations", []) == []


def test_policy_fails_on_forbidden_api(tmp_path: Path):
    (tmp_path / "main.py").write_text("x = eval('2+2')\n")

    rule = Rule({"forbidden_apis": ["eval"], "forbidden_packages": []})
    passed, message, details = rule.execute({"absolute_path": str(tmp_path)})

    assert passed is False
    assert details.get("violations")


def test_policy_collects_used_distributions(monkeypatch, tmp_path: Path):
    (tmp_path / "main.py").write_text("import yaml\n")

    rule = Rule({"forbidden_packages": [], "forbidden_apis": []})
    monkeypatch.setattr(rule, "_top_level_import_to_distributions", lambda name: ["PyYAML"])

    passed, message, details = rule.execute({"absolute_path": str(tmp_path)})

    assert passed is True
    assert details["used_distributions"] == ["PyYAML"]
