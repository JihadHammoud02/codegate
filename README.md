# CodeGate

**CodeGate** is a **contract-driven evaluator for Python code**.

You define *what “acceptable code” means* in a YAML contract (environment, tests, security, policies).
CodeGate executes those rules **deterministically**, usually inside an **isolated Docker container**, and produces a **machine-readable JSON verdict**.

Built for **AI-generated code**, but works for any Python project.

---

## Why CodeGate

- **Contracts over vibes** — success is explicit, versioned, and reviewable.
- **Reproducible** — evaluation runs in a pinned runtime image.
- **Explainable failures** — every failure includes concrete evidence.
- **One command** — build, test, scan, and policy-check in one run.

> CodeGate does not judge *style* or *quality*.
> It answers one question: **“Does this code satisfy the contract?”**

---

## How It Works (Mental Model)

```text
(YAML Contract)
      ↓
[ Isolated Runtime ]
      ↓
[ Deterministic Rules ]
      ↓
Structured JSON Verdict
```

---

## Install

```bash
pip install -e .

# Dev tools (tests, linters, etc.)
pip install -e ".[dev]"
```

### Requirements

- Python $\ge 3.8$
- Docker (recommended). Without Docker, some rules may be skipped or fail depending on your environment.

---

## Quick Start

### 1) Define a Contract

```yaml
Environment:
  runtime_image: python:3.9-slim
  network_access: false
  file_system_access: false

project:
  path: ./

rules:
  build_imports:
    enabled: true

  unit_tests:
    enabled: true
    coverage_threshold: 80

  security_sast:
    enabled: true

  policy:
    enabled: true
    forbidden_apis: ["eval", "exec", "os.system"]
```

### 2) Run

```bash
codegate run contract.yaml
```

### 3) Get a Verdict

```json
{
  "summary": {
    "passed": 3,
    "failed": 1,
    "success_rate": 75.0
  },
  "results": [
    {
      "rule": "policy",
      "passed": false,
      "message": "Forbidden API used: eval",
      "evidence": {
        "file": "main.py",
        "line": 42
      }
    }
  ]
}
```

---

## Contract Sections (Minimal)

### Environment

Defines *where* code is evaluated.

```yaml
Environment:
  runtime_image: python:3.10-slim
  network_access: false
  allowed_writing_paths: ["/tmp"]
```

**Failure example**

- Code tries to call an external API → **blocked network syscall**

---

### Project

Defines *what* is evaluated.

```yaml
project:
  path: ./
  entry_point: main.py
  python_dependencies:
    - requests>=2.25
```

**Failure example**

- Missing dependency → `ImportError: No module named requests`

---

## Rules (Core of CodeGate)

Rules are **independent** and **opt-in**.

---

### `build_imports`

Verifies all imports resolve.

```yaml
build_imports:
  enabled: true
```

**Fails when**

- Missing dependency
- Circular import crash
- Import timeout

**Evidence**

- Python traceback
- Module name that failed

---

### `unit_tests`

Runs tests and enforces coverage.

```yaml
unit_tests:
  enabled: true
  coverage_threshold: 85
```

**Fails when**

- Any test fails
- Coverage < threshold

**Evidence**

- Failing test names
- Coverage report

---

### `security_sast`

Static security analysis (Bandit).

```yaml
security_sast:
  enabled: true
```

**Fails when**

- Use of `eval`, `pickle`, weak crypto, etc.

**Evidence**

- Rule ID (e.g. `B307`)
- File + line number

---

### `security_deps`

Checks dependencies for known CVEs.

```yaml
security_deps:
  enabled: true
```

**Fails when**

- Vulnerable dependency detected

**Evidence**

- Package name
- CVE ID
- Severity

---

### `policy`

Hard usage constraints.

```yaml
policy:
  enabled: true
  forbidden_modules: ["subprocess"]
  forbidden_packages: ["boto3"]
  forbidden_apis: ["os.system", "eval"]
```

**Fails when**

- Forbidden import
- Forbidden API call
- Forbidden dependency installed

**Evidence**

- File, line, symbol name

---

## Rule Outcomes

Each rule produces one of:

- **PASS** — contract satisfied
- **FAIL** — contract violated (with evidence)
- **SKIPPED** — disabled or unsupported
- **ERROR** — evaluator failure (tooling issue)

Final outcome is derived from rule results, not heuristics.

---

## Security Model (Important)

When Docker is enabled:

- Optional `--network=none`
- Read-only project mount
- Limited write paths
- Resource limits

⚠️ **Not a sandbox**. Still treat untrusted code carefully.

---

## CLI

```bash
codegate run contract.yaml
codegate validate contract.yaml
codegate --version
```

---

## Docs / Architecture

- Diagrams: `docs/README.md`
- Package overview: `codegate/README.md`
- Engine: `codegate/engine/README.md`
- Contracts: `codegate/contract/README.md`
- Rules: `codegate/rules/README.md`
- Examples: `examples/README.md`

---

## What CodeGate Is *Not*

- ❌ A code generator
- ❌ A prompt optimizer
- ❌ A style or lint judge
- ❌ A replacement for human review

It is an **automated gate**, not an approval stamp.

---

## License

MIT
