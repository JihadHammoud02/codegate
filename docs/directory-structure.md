# Directory tree & relationships

```text
codegate/
├─ cli.py                 # CLI entrypoint (parses args, loads contract, runs Runner)
├─ contract/
│  ├─ parser.py            # YAML loader -> dict/Contract
│  └─ schema.py            # Contract validation (what keys/sections are allowed)
├─ engine/
│  ├─ runner.py            # Orchestrates: build deps image once, then executes rules
│  ├─ docker_runner.py     # Docker utility: build_deps_image + run_command
│  └─ result.py            # Result dataclasses/structs (RuleResult, EvaluationResult)
└─ rules/
   ├─ base.py              # BaseRule interface (execute contract)
   ├─ build_imports.py     # compileall + import entry point (in container)
   ├─ unit_tests.py        # pytest + coverage (in container)
   ├─ security_sast.py     # bandit (in container)
   ├─ security_deps.py     # pip-audit / safety (in container)
   └─ policy.py            # AST policy checks (local)

examples/
└─ sample_project/
   ├─ contract.yaml        # Example contract in the new schema
   └─ ...                  # Toy project to scan/test

tests/
└─ ...                     # Unit tests for parser/runner/rules
```

## Relationship overview

- `cli.py` is the entry point.
- `contract/parser.py` reads YAML → Python dict (and/or structured object).
- `contract/schema.py` validates the contract.
- `engine/runner.py`:
  - builds a Docker deps image from the contract (via `engine/docker_runner.py`)
  - loads rule modules dynamically (`codegate.rules.<rule_name>`)
  - calls `Rule.execute(artifact_info)` for each enabled rule
- Rules either:
  - run commands inside containers (build/test/security rules)
  - or perform local static checks (policy)
