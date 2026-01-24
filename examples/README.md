# `examples/`

Example contracts and a small sample project to demonstrate CodeGate.

## Contents

- `contract-minimal.yaml` — minimal contract example
- `contract-security-only.yaml` — run only security rules
- `contract-testing-only.yaml` — run only unit tests
- `contract-with-custom-rule.yaml` — example for extending CodeGate
- `sample_project/` — toy Python project + contract used for smoke testing

## Try the sample project

```bash
cd examples/sample_project
codegate run contract.yaml --verbose
```
