# `codegate/contract/`

Contract parsing and validation.

## Files

- `parser.py` — loads YAML contracts and returns a parsed contract dict
- `schema.py` — validates contract structure and rule configs

## Responsibilities

- Ensure the contract includes the expected sections (`Environment`, `project`, `rules`)
- Provide helpful validation errors if a contract is malformed
