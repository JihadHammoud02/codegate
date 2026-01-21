# CodeGate

CodeGate is a contract-driven evaluator that runs deterministic build, test, security, policy, and quality gates on Python AI-generated code.

## Features

- **Contract-based evaluation**: Define your quality gates in a YAML contract
- **Multiple artifact types**: Support for Python packages, scripts, and Docker images
- **Extensible rules**: Easy-to-add custom evaluation rules
- **Docker integration**: Run evaluations in isolated containers
- **Detailed reporting**: Get comprehensive JSON reports of all checks

## Installation

```bash
# Install from source
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

### 1. Create a Contract

Create a `contract.yaml` file defining your evaluation criteria:

```yaml
project:
  name: my-project
  version: 1.0.0

artifact:
  type: python-package
  path: ./src

rules:
  syntax-check: true
  lint-check: true
  type-check: true
  test-coverage:
    enabled: true
    min_coverage: 80
  security-scan: true
```

### 2. Run Evaluation

```bash
codegate run contract.yaml
```

### 3. View Results

Results are saved to `codegate-results.json` by default:

```json
{
  "project": "my-project",
  "summary": {
    "total": 5,
    "passed": 4,
    "failed": 1,
    "success_rate": 80.0,
    "duration": 12.345
  },
  "results": [
    {
      "rule": "syntax-check",
      "passed": true,
      "message": "All 15 files have valid syntax",
      "details": {"files_checked": 15},
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
│       ├── syntax_check.py
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
