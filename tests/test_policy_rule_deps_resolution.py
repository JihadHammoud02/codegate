from __future__ import annotations

import ast

from codegate.rules.policy import Rule


def test_policy_forbidden_packages_uses_resolved_distribution(monkeypatch, tmp_path):
    py = tmp_path / "x.py"
    py.write_text("import yaml\n")

    tree = ast.parse(py.read_text(), filename=str(py))

    rule = Rule({"forbidden_packages": ["PyYAML"]})

    # Pretend `import yaml` maps to distributions ["PyYAML"]
    monkeypatch.setattr(rule, "_top_level_import_to_distributions", lambda name: ["PyYAML"])

    used = set()
    violations = rule._check_imports(tree, py, forbidden_packages={"PyYAML"}, used_distributions=used)
    assert len(violations) == 1
    assert violations[0]["package"] == "PyYAML"
    assert violations[0]["import"] == "yaml"
    assert used == {"PyYAML"}


def test_policy_forbidden_packages_ignores_unresolved(monkeypatch, tmp_path):
    py = tmp_path / "x.py"
    py.write_text("import does_not_exist\n")

    tree = ast.parse(py.read_text(), filename=str(py))

    rule = Rule({"forbidden_packages": ["Something"]})
    monkeypatch.setattr(rule, "_top_level_import_to_distributions", lambda name: [])

    used = set()
    violations = rule._check_imports(tree, py, forbidden_packages={"Something"}, used_distributions=used)
    assert violations == []
    assert used == set()
