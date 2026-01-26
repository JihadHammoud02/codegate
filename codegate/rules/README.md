# `codegate/rules/`

Built-in rules for evaluating a project.

## How rules work

Each rule is a Python module that exposes a `Rule` class implementing:

- `execute(artifact_info) -> (passed: bool, message: str, details: dict)`

Rules are loaded dynamically by name from the contract:

- Contract key: `build_imports`
- Module path: `codegate.rules.build_imports`
- Class name: `Rule`

## Built-in rules

- `build_imports` — compiles Python files and imports the declared entry point
- `unit_tests` — runs `pytest` (optionally with coverage threshold)
- `security_sast` — runs Bandit (SAST)
- `security_deps` — runs dependency vulnerability tooling (pip-audit / safety when available)
- `policy` — local AST-based checks for forbidden modules/packages/APIs

## Notes

- Most rules run inside Docker using the pre-built deps image.
- `policy` is static analysis and runs locally.
