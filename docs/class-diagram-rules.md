# Class diagram — Rules

```mermaid
classDiagram
    direction TB

    class BaseRule {
      +__init__(config: Dict)
      +name: str
      +config: Dict
      +enabled: bool
      +execute(artifact_info: Dict) (bool, str, Dict)
    }

    class BuildImportsRule {
      +import_timeout: int
      +execute(artifact_info)
      -_phase_compile(...)
      -_phase_import(...)
    }

    class UnitTestsRule {
      +test_directory: str
      +coverage_threshold: int
      +timeout: int
      +execute(artifact_info)
    }

    class SecuritySASTRule {
      +severity_level: str
      +execute(artifact_info)
    }

    class SecurityDepsRule {
      +execute(artifact_info)
    }

    class PolicyRule {
      +forbidden_modules: List[str]
      +forbidden_packages: List[str]
      +forbidden_apis: List[str]
      +execute(artifact_info)
      -_scan_file(path)
      -_analyze_ast(tree)
    }

    BaseRule <|-- BuildImportsRule
    BaseRule <|-- UnitTestsRule
    BaseRule <|-- SecuritySASTRule
    BaseRule <|-- SecurityDepsRule
    BaseRule <|-- PolicyRule

    class Runner {
      +run() EvaluationResult
      -_prepare_environment() None
      -_run_rule(rule_config) RuleResult
      -_load_rule_module(rule_name)
    }

    class DockerRunner {
      +build_deps_image(runtime_image, system_deps, python_deps) str
      +run_command(image, command, project_path, network_access, writable, timeout)
    }

    Runner --> DockerRunner : builds deps image + runs commands
    BuildImportsRule --> DockerRunner : run_command()
    UnitTestsRule --> DockerRunner : run_command()
    SecuritySASTRule --> DockerRunner : run_command()
    SecurityDepsRule --> DockerRunner : run_command()
```

### Notes
- In each rule file, the concrete class is named `Rule` (loaded dynamically), but conceptually it maps to the rule type shown above.
- `artifact_info` is the shared context passed from `Runner` → each `Rule.execute(...)` and contains keys like `docker_runner`, `deps_image`, `absolute_path`, `network_access`, etc.
