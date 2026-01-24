\
# CodeGate

CodeGate is a **contract-driven evaluator** for Python projects.

You describe what “good” looks like in a YAML contract (build checks, unit tests, security gates, policy rules), and CodeGate runs those gates **deterministically**—preferably inside **isolated Docker containers**—and produces a structured JSON report.

It’s designed for evaluating **AI-generated code**, but it works for any Python project.

## Why CodeGate

- **Contract-first**: your evaluation rules live in versioned YAML, not hidden CI scripts.
- **Reproducible**: the contract pins the runtime image + dependencies used for evaluation.
- **Secure-by-default**: optional network isolation and restricted write access.
- **Actionable output**: a single JSON report with per-rule details.

## Features

- YAML contract schema with `Environment`, `project`, and `rules`
- Docker dependency image built once per run (runtime + system deps + python deps)
- Built-in rules for build/import checks, unit tests, SAST, dependency vulns, and policy enforcement
- Extensible rule system (drop-in rule modules)

## Installation

```bash
pip install -e .

# Dev tools (tests, linters, etc.)
pip install -e ".[dev]"
```

### Requirements

- Python $\ge 3.8$
- Docker (recommended). Without Docker, some rules may be skipped or fail depending on your environment.

## Quick Start

### 1. Create a Contract

Create a `contract.yaml` file defining your evaluation criteria:

```yaml
Environment:
  runtime_image: python:3.9-slim
  network_access: false
  file_system_access: false
  allowed_writing_paths: ["/tmp", "/var/tmp"]
  system_dependencies: ["build-essential"]

project:
  path: ./
  entry_point: main.py
  python_dependencies:
    - requests>=2.25.0

rules:
  build_imports:
    enabled: true
    import_timeout: 120
  
  unit_tests:
    enabled: true
    test_directory: tests/
    coverage_threshold: 85
  
  security_sast:
    enabled: true
  
  security_deps:
    enabled: true
  
  policy:
    enabled: true
    forbidden_modules: ["os", "subprocess"]
    forbidden_packages: ["boto3"]
    forbidden_apis: ["os.system", "eval", "exec"]
```

### 2. Run Evaluation

```bash
codegate run contract.yaml --verbose
```

### 3. View Results

Results are saved to `codegate-results.json` by default:

```json
{
  "project": "python:3.9-slim",
  "artifact_type": "docker-container",
  "summary": {
    "total": 5,
    "passed": 4,
    "failed": 1,
    "success_rate": 80.0,
    "duration": 12.345
  },
  "results": [
    {
      "rule": "build_imports",
      "passed": true,
      "message": "All imports resolved successfully",
      "details": {"imports_tested": ["main"]},
      "duration": 0.234
    }
  ]
}
```

## Project Structure

```
codegate/
├── codegate/              # Main package
│   ├── __init__.py
│   ├── cli.py            # Command-line interface
│   ├── contract/         # YAML parsing & validation
│   │   ├── __init__.py
│   │   ├── parser.py     # Contract parser
│   │   └── schema.py     # Schema validator
│   ├── engine/           # Rule execution engine
│   │   ├── __init__.py
│   │   ├── runner.py     # Main evaluation runner
│   │   ├── result.py     # Result classes
│   │   └── docker_runner.py  # Docker integration
│   └── rules/            # Individual rule implementations
│       ├── __init__.py
│       ├── base.py       # Base rule class
│       ├── build_imports.py  # Import resolution check
│       ├── unit_tests.py     # Unit test execution
│       ├── security_sast.py  # SAST security scanning
│       ├── security_deps.py  # Dependency vulnerability check
│       └── policy.py         # Policy enforcement
├── examples/
│   ├── contract-minimal.yaml
│   └── sample_project/
│       ├── contract.yaml
│       ├── calculator.py
│       └── test_calculator.py
├── tests/                # Unit tests
├── README.md
├── pyproject.toml
└── requirements.txt
```

For more detailed module documentation, see:

- `codegate/README.md`
- `codegate/engine/README.md`
- `codegate/contract/README.md`
- `codegate/rules/README.md`
- `examples/README.md`
- `docs/README.md`

## Contract Schema

### Required Sections

#### Environment
Defines the Docker runtime environment:
- `runtime_image`: Docker base image (e.g., `python:3.9-slim`)
- `network_access`: Boolean - allow network access
- `file_system_access`: Boolean - allow file system access
- `allowed_writing_paths`: List of allowed write directories
- `system_dependencies`: List of system packages to install

#### project
Defines the Python project:
- `path`: Path to project directory
- `entry_point`: Main Python file (optional)
- `python_dependencies`: List of pip packages (optional)

#### rules
Defines evaluation rules to run:

**build_imports**: Verify all imports can be resolved
- `enabled`: Boolean
- `import_timeout`: Timeout in seconds (optional)

**unit_tests**: Run unit tests with coverage
- `enabled`: Boolean
- `test_directory`: Path to tests (optional)
- `coverage_threshold`: Minimum coverage % (optional)

**security_sast**: Static security analysis
- `enabled`: Boolean

**security_deps**: Check for vulnerable dependencies
- `enabled`: Boolean

**policy**: Enforce usage policies
- `enabled`: Boolean
- `forbidden_modules`: List of module names (optional)
- `forbidden_packages`: List of package names (optional)
- `forbidden_apis`: List of API calls (optional)

### Rule Selection Flexibility

**You can use any combination of rules you want:**

- ✅ Use all 5 rules
- ✅ Use just 1 rule
- ✅ Use any subset of rules
- ✅ Disable specific rules by setting `enabled: false`
- ✅ Use empty rules section (`rules: {}`) to skip all evaluations

**Examples:**

```yaml
# Use only security rules
rules:
  security_sast:
    enabled: true
  security_deps:
    enabled: true
```

```yaml
# Use only import checks with custom timeout
rules:
  build_imports:
    enabled: true
    import_timeout: 120
```

```yaml
# Use all rules with custom configurations
rules:
  build_imports:
    enabled: true
    import_timeout: 60
  unit_tests:
    enabled: true
    test_directory: tests/
    coverage_threshold: 85
  security_sast:
    enabled: true
  security_deps:
    enabled: true
  policy:
    enabled: true
    forbidden_modules: ["yaml", "pickle"]
    forbidden_packages: ["boto3"]
    forbidden_apis: ["os.system"]
```

```yaml
# No rules - just environment setup
rules: {}
```

## Available Rules

### build_imports
Verifies that all Python imports can be resolved and no import errors occur.

### unit_tests
Runs unit tests using pytest or unittest and checks code coverage against a threshold.

### security_sast
Performs static application security testing using bandit to find security issues.

### security_deps
Checks Python dependencies for known vulnerabilities using pip-audit or safety.

### policy
Enforces custom policies by detecting forbidden:
- Module imports
- Package usage
- API calls

## Security model (high level)

When Docker is enabled, rules run inside containers with:

- optional `--network=none` when `network_access: false`
- the project mounted into `/workspace` (read-only for most rules)
- resource limits (CPU/memory) to reduce blast radius

**Note:** CodeGate is a safety tool, not a full sandbox. Treat untrusted code accordingly.

## CLI Commands

### Run Evaluation
```bash
codegate run <contract.yaml> [--verbose] [--output <file>]
```

Options:
- `--verbose`, `-v`: Enable verbose output
- `--output`, `-o`: Output file path (default: codegate-results.json)

### Validate Contract
```bash
codegate validate <contract.yaml>
```

### Show Version
```bash
codegate --version
```

## Docs

Architecture diagrams (Mermaid) live in `docs/`:

- `docs/sequence-diagram.md`
- `docs/directory-structure.md`
- `docs/class-diagram-rules.md`

## Contributing

PRs are welcome. If you’re adding a rule:

1. Create a new module in `codegate/rules/` exporting a `Rule` class.
2. Add tests under `tests/`.
3. Document the rule’s contract config in the top-level README.

## License

MIT (see `LICENSE` if present).

## Examples

### Minimal Contract
```yaml
Environment:
  runtime_image: python:3.9-slim
  network_access: false
  file_system_access: false

project:
  path: ./
  entry_point: main.py

rules:
  build_imports:
    enabled: true
  security_sast:
    enabled: true
  security_deps:
    enabled: true
  unit_tests:
    enabled: false
  policy:
    enabled: false
```

### Strict Security Contract
```yaml
Environment:
  runtime_image: python:3.9-slim
  network_access: false
  file_system_access: false
  allowed_writing_paths: ["/tmp"]

project:
  path: ./
  entry_point: app.py
  python_dependencies:
    - flask>=2.0.0

rules:
  build_imports:
    enabled: true
  
  unit_tests:
    enabled: true
    test_directory: tests/
    coverage_threshold: 90
  
  security_sast:
    enabled: true
  
  security_deps:
    enabled: true
  
  policy:
    enabled: true
    forbidden_modules: ["pickle", "marshal", "shelve"]
    forbidden_packages: ["boto3", "paramiko"]
    forbidden_apis: ["eval", "exec", "__import__", "os.system"]
```
│       ├── lint_check.py
│       ├── type_check.py
│       ├── test_coverage.py
│       └── security_scan.py
├── tests/                # Test suite
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_runner.py
│   └── test_syntax_check.py
├── examples/             # Example contracts
│   ├── contract-python-package.yaml
│   └── contract-docker.yaml
├── pyproject.toml       # Project configuration
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Contract Schema

### Project Section

```yaml
project:
  name: string          # Project name (required)
  version: string       # Version (optional)
  description: string   # Description (optional)
```

### Artifact Section

```yaml
artifact:
  type: string         # python-package | python-script | docker-image (required)
  path: string         # Path to artifact (required)
  image: string        # Docker image name (for docker-image type)
```

### Rules Section

Rules can be configured as boolean (enabled/disabled) or with detailed options:

```yaml
rules:
  # Simple enable/disable
  syntax-check: true
  
  # With configuration
  test-coverage:
    enabled: true
    min_coverage: 80
  
  lint-check:
    enabled: true
```

## Available Rules

| Rule | Description | Configuration |
|------|-------------|---------------|
| `syntax-check` | Validates Python syntax | None |
| `lint-check` | Runs code linting (flake8) | None |
| `type-check` | Validates type hints (mypy) | None |
| `test-coverage` | Checks test coverage | `min_coverage: float` |
| `security-scan` | Scans for security issues (bandit) | None |

## Docker Support

CodeGate can evaluate Docker-based artifacts:

```yaml
artifact:
  type: docker-image
  path: ./project-dir    # Directory containing Dockerfile
  image: my-app          # Image name
```

The evaluator will:
1. Build the Docker image (if Dockerfile present)
2. Run evaluation rules inside the container
3. Report results

## Development

### Running Tests

```bash
pytest tests/
```

### Running Tests with Coverage

```bash
pytest --cov=codegate tests/
```

### Adding a New Rule

1. Create a new file in `codegate/rules/` (e.g., `my_rule.py`)
2. Implement the `Rule` class inheriting from `BaseRule`:

```python
from .base import BaseRule
from typing import Dict, Any, Tuple

class Rule(BaseRule):
    def execute(self, artifact_info: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        # Your rule logic here
        passed = True
        message = "Rule passed"
        details = {"key": "value"}
        return passed, message, details
```

3. Use the rule in your contract:

```yaml
rules:
  my-rule:
    enabled: true
```

## CLI Commands

### Run Evaluation

```bash
codegate run contract.yaml [--output results.json] [--verbose]
```

Options:
- `--output`, `-o`: Output file path (default: `codegate-results.json`)
- `--verbose`, `-v`: Enable verbose output

### Show Version

```bash
codegate version
```

## Examples

See the `examples/` directory for sample contracts:

- `contract-python-package.yaml`: Evaluation for Python packages
- `contract-docker.yaml`: Evaluation for Docker-based projects

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
