# Codegate

> **A contract-driven observatory for evaluating LLM-generated code — before humans review it.**

Codegate is a **developer-first evaluation engine** designed to *systematically assess AI‑generated code* against **explicit, user-defined contracts**. Instead of asking *“does this code look good?”*, Codegate answers a much more useful question:

> **“Does this code satisfy *****my***** constraints, in *****my***** environment, with evidence?”**

This project is intentionally opinionated, minimal, and infra-oriented. It is not a chatbot, not a prompt optimizer, and not a benchmark. It is a **verification layer**.

**Codegate is not a replacement for human code review**: it exists to automate well-defined verification steps and surface objective evidence, so human reviewers can focus their expertise where it matters most.

---

## Project Information

### Project name

**Codegate**

### Short description

A contract-based evaluation engine that validates LLM-generated code using declarative rules, isolated execution, and explainable failure reports.

### Main purpose / problem solved

LLM-generated code is increasingly used, but **cannot be trusted by default**:

- It may compile but violate hidden constraints
- It may pass tests but use forbidden APIs
- It may work locally but fail in the target environment
- It may be insecure, non-compliant, or unreviewable at scale

Codegate solves this by introducing a **Code Success Contract**: a machine-readable specification that defines *what success means* **before** code is reviewed by a human.

---

## Target Users

- **Software engineers** validating AI-generated pull requests
- **AI / platform engineers** building LLM-based developer tooling
- **Security & reliability engineers** enforcing policy on generated code
- **Researchers** studying LLM failure modes in code generation

If you care about **correctness, reproducibility, security, or explainability**, this tool is for you.

---

## Tech Stack / Language

- **Language:** Python 3.10+
- **Execution:** Docker (sandboxed, network-restricted)
- **Config:** YAML (human-readable contracts)
- **Testing:** pytest / custom runners
- **Static analysis:** AST parsing, regex rules, optional linters

No model inference. No prompt engineering. Pure evaluation.

---

## Main Features

- **Declarative success contracts** (`.yaml`)
- **One-command evaluation** of generated code
- **Isolated Docker execution** (env parity, no network)
- **Static policy enforcement** (forbidden modules, APIs, packages)
- **Test-based behavioral validation**
- **Explainable failure reports** with evidence
- **Clear outcome classification** (success / soft fail / hard fail / uncertain)

---

## Installation

```bash
pip install codegate
```

Or from source:

```bash
git clone https://github.com/<your-username>/codegate.git
cd codegate
pip install -e .
```

Requirements:

- Python 3.10+
- Docker (running)

---

## Usage Examples

### Basic command

```bash
codegate run \
  --code ./generated_code \
  --contract ./contract.yaml
```

This single command will:

1. Build an isolated execution environment
2. Compile / import the code
3. Run tests
4. Enforce security & policy rules
5. Produce a structured evaluation report

---

## YAML Contract Schema (Core Abstraction)

The **contract** defines success. Nothing is implicit.

### Example: `contract.yaml`

```yaml
project:
  language: python
  python_version: "3.11"

execution:
  docker:
    base_image: python:3.11-slim
    network_access: false
    timeout_seconds: 30

policy:

  forbidden_packages:
    - pyyaml
    - pycryptodome
    - scikit-learn

  forbidden_apis:
    - eval
    - exec
    - os.system
    - subprocess.Popen
    - importlib.import_module

tests:
  framework: pytest
  path: tests/

success_criteria:
  require_all_tests_pass: true
  max_warnings: 0
```

### Design principles

- **Declarative, not procedural**
- **Readable by humans**
- **Extensible but minimal**
- **Auditable**

---

## Rules (Core of CodeGate)

Rules are **independent**, **opt‑in**, and evaluated in isolation. Each rule represents a distinct failure mode commonly observed in LLM‑generated code. Together, they act as *quality gates* that catch issues **before** human review.

---

### `build_imports`

**Definition:** Verifies that all imports resolve correctly in the target environment.

**Why it matters:** LLM‑generated code frequently references packages, modules, or transitive dependencies that do not exist in the actual runtime. These failures are trivial but costly when discovered late.

**Example:** A model imports `requests_cache` because it appeared in training data, but the dependency is not allowed or installed. `build_imports` fails fast, preventing wasted debugging time.

**Typical failures caught:**

- Missing dependency
- Circular import crash
- Import hang or timeout

---

### `unit_tests`

**Definition:** Executes the project’s test suite and optionally enforces a coverage threshold.

**Why it matters:** Passing tests remain the strongest signal of behavioral correctness, especially when humans did not write the code.

**Example:** Generated code passes basic functionality but fails edge‑case tests or silently reduces coverage. This rule ensures regressions are explicit and measurable.

**Typical failures caught:**

- Failing assertions
- Untested code paths
- Behavior drift masked by partial test success

---

### `security_sast`

**Definition:** Performs static application security testing using tools like Bandit.

**Why it matters:** LLMs may generate insecure patterns that *work correctly* but introduce severe vulnerabilities.

**Example:** Code uses `pickle.loads` for convenience. Tests pass, but `security_sast` flags this as unsafe deserialization with a precise rule ID and location.

**Typical failures caught:**

- Use of `eval` / `exec`
- Insecure cryptography
- Unsafe serialization

---

### `security_deps`

**Definition:** Scans declared dependencies for known vulnerabilities (CVEs).

**Why it matters:** Even correct code becomes a liability if it depends on vulnerable libraries.

**Example:** Generated code introduces `urllib3<1.26`. Tests pass, but the dependency scan detects a high‑severity CVE and blocks integration.

**Typical failures caught:**

- Known vulnerable packages
- High‑severity transitive CVEs

---

### `policy`

**Definition:** Enforces hard organizational constraints on packages and APIs.

**Why it matters:** Some constraints are non‑negotiable and cannot be inferred from tests alone.

**Example:** Even if code works perfectly, importing `subprocess` or calling `os.system` may violate sandboxing or compliance rules. The policy gate encodes these rules explicitly.

**Typical failures caught:**

- Forbidden API usage
- Disallowed dependencies

---

**Key idea:** Each rule targets a *different dimension of risk* — correctness, security, compliance, or reliability.

By enforcing these gates automatically, CodeGate ensures that human reviewers spend their time on **design, intent, and maintainability**, not on catching avoidable failures.

---

## Project Structure

```text
codegate/
  cli.py                 # `codegate` entrypoint + `run` subcommand
  contract/
    parser.py            # YAML loading
    schema.py            # contract validation (types, required fields)
  engine/
    runner.py            # orchestration: build deps image once, run enabled rules
    docker_runner.py     # docker build/run helpers (network + mounts + limits)
    result.py            # RuleResult / EvaluationResult -> JSON
  rules/
    base.py              # rule interface
    build_imports.py     # compile + import checks (docker)
    unit_tests.py        # pytest execution + parsing (docker)
    security_sast.py     # bandit scanning (docker)
    security_deps.py     # pip-audit / safety (docker)
    policy.py            # local AST policy: forbidden packages + APIs

tests/
  ...                    # unit + integration tests (docker interactions mocked)
docs/
  ...                    # diagrams + design notes
```

---

## How It Runs (Technical Design)

At a high level, Codegate executes your contract as a **pipeline of rules** and produces a single JSON report.

### 1) Parse + validate the contract

- The CLI loads your YAML file.
- The contract is validated (required fields, types, rule-specific config).

### 2) Build a reusable dependency image (Docker)

For Docker-based rules, Codegate builds **one** dependency image per evaluation:

- Starts from `Environment.runtime_image`
- Installs optional system packages from `Environment.system_dependencies`
- Installs Python deps from:
  - `project.python_dependencies`
  - and optional `requirements.txt` in the project folder

This image is cached by a hash of the config so repeated runs are fast.

### 3) Execute enabled rules

Rules are executed independently and contribute results to the final report.

- Docker-based rules run inside the dependency image, with:
  - optional network isolation (`Environment.network_access: false` → `--network=none`)
  - workspace mounted at `/workspace`
- The `policy` rule runs locally (static AST scan) to keep it fast and deterministic.

### 4) Emit a structured report

The output includes:

- per-rule pass/fail + message
- details/evidence (parsed tool output)
- a summary with totals + timing

This report is meant to be consumed by:

- humans (review evidence)
- automation (gate merges, fail CI, research analysis)



---

## Outcome Classification

Codegate reports results as **per-rule outcomes** plus an overall summary.

Practically, you can interpret results using the following classification:

- **Success**: all enabled rules passed.
- **Hard fail**: one or more enabled rules failed (e.g. tests failed, forbidden dependency used, vulnerability found).
- **Uncertain / skipped checks**: a rule may report that it was skipped because a tool isn’t available (for example: no scanner installed inside the image). This is still a *pass* for the rule, but the report will include a warning/detail so you can decide if “skipped” is acceptable in your environment.

In other words:

- A clean pass means “contract satisfied”.
- A fail means “contract violated”.
- A skip means “not enough evidence to evaluate that check”, and you can tighten the environment/contract to prevent skipping.



---


## Status

🚧 **Beta — actively evolving**

Feedback from engineers, researchers, and infra-minded people is highly welcome.

