# `codegate/`

This package contains the CodeGate CLI and evaluation engine.

## What lives here

- `cli.py` — command line interface (entrypoint for the `codegate` command)
- `contract/` — YAML parsing + schema validation
- `engine/` — orchestration logic + Docker integration
- `rules/` — built-in rules (build/test/security/policy)

If you’re browsing the code, start with:

1. `cli.py`
2. `engine/runner.py`
3. `engine/docker_runner.py`
4. `rules/*`
