# codegate

codegate is a contract-driven evaluator that runs deterministic build, test, security, policy, and quality gates on AI-generated code.

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

```bash
codegate run <contract.yaml>
```

This command loads a YAML contract file and evaluates code according to the rules defined in the contract. The command does not modify any code - it only evaluates it.

### Contract Structure

A contract is a YAML file that defines rules to evaluate code. Here's an example:

```yaml
rules:
  build_import:
    command: "python -m py_compile my_code.py"
  
  unit_tests:
    command: "python -m pytest tests/ -v"
  
  security_sast:
    command: "bandit -r src/"
    acceptable_exit_codes: [0]
  
  security_deps:
    command: "safety check"
    acceptable_exit_codes: [0]
  
  policy:
    command: "custom-policy-checker"
    acceptable_exit_codes: [0]
  
  quality:
    command: "pylint src/"
    acceptable_exit_codes: [0]
```

## Available Rules

codegate supports the following modular rules:

1. **build_import** - Validates that code can be imported or built successfully
2. **unit_tests** - Runs unit tests and validates they pass
3. **security_sast** - Performs static application security testing
4. **security_deps** - Checks for vulnerable dependencies
5. **policy** - Validates code against custom policy requirements
6. **quality** - Validates code quality metrics

Each rule:
- Outputs a status: **PASS**, **FAIL**, or **ERROR**
- Stores JSON artifacts in `.artifacts/<rule>/result.json`
- Stores command output in `.artifacts/<rule>/output.txt`

## Rule Configuration

Each rule accepts the following configuration options:

- `command`: The command to execute (required)
- `acceptable_exit_codes`: List of exit codes considered as success (optional, defaults to [0])

## Exit Codes

- `0`: All rules passed
- `1`: One or more rules failed or encountered an error

## Example

See `example_contract.yaml`, `example_code.py`, and `example_test.py` for a complete working example.

```bash
# Run the example
codegate run example_contract.yaml
```

## Artifacts

All rule execution artifacts are stored in `.artifacts/<rule>/`:
- `result.json`: JSON output with status and metadata
- `output.txt`: Full command output (stdout and stderr)

The `.artifacts/` directory is automatically created and is gitignored by default.
