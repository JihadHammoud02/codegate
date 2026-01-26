from __future__ import annotations

from pathlib import Path

from codegate.rules.policy import Rule


def test_policy_forbidden_packages_are_resolved_against_installed_distributions(monkeypatch, tmp_path: Path):
    # Project imports 'yaml' which resolves to 'PyYAML'
    (tmp_path / "main.py").write_text("import yaml\n")

    rule = Rule({"forbidden_packages": ["pyyaml"], "forbidden_apis": []})

    # Pretend installed dists include PyYAML (normalize -> canonical)
    monkeypatch.setattr(rule, "_installed_distributions_normalized", lambda: {"pyyaml": "PyYAML"})
    # Pretend import resolves to distribution PyYAML
    monkeypatch.setattr(rule, "_resolve_top_level_distribution", lambda module: "PyYAML")

    passed, message, details = rule.execute({"absolute_path": str(tmp_path)})

    assert passed is False
    assert details["forbidden_packages_normalized"] == ["PyYAML"]
    assert any(v["type"] == "forbidden_dependency" and v["package"] == "PyYAML" for v in details["violations"])


def test_policy_forbidden_packages_unknown_names_are_ignored(monkeypatch, tmp_path: Path):
    (tmp_path / "main.py").write_text("import yaml\n")

    rule = Rule({"forbidden_packages": ["definitely-not-installed"], "forbidden_apis": []})

    monkeypatch.setattr(rule, "_installed_distributions_normalized", lambda: {"pyyaml": "PyYAML"})
    monkeypatch.setattr(rule, "_resolve_top_level_distribution", lambda module: "PyYAML")

    passed, message, details = rule.execute({"absolute_path": str(tmp_path)})

    # No forbidden packages resolved -> no dependency violations.
    assert passed is True
    assert details["forbidden_packages_normalized"] == []
    assert details["used_distributions"] == ["PyYAML"]
