# Sequence diagram — `codegate run`

```mermaid
sequenceDiagram
    autonumber

    actor User
    participant CLI as codegate/cli.py
    participant Parser as contract/parser.py
    participant Schema as contract/schema.py
    participant Runner as engine/runner.py
    participant Docker as engine/docker_runner.py
    participant Rule as rules/<rule>.py
    participant DockerEngine as Docker daemon

    User->>CLI: codegate run contract.yaml [--verbose]
    CLI->>Parser: load_contract(contract.yaml)
    Parser->>Schema: validate(contract_dict)
    Schema-->>Parser: validated contract
    Parser-->>CLI: Contract object/dict

    CLI->>Runner: Runner(contract).run()

    Note over Runner: Prepare environment once
    Runner->>Docker: build_deps_image(runtime_image, system_deps, python_deps)
    Docker->>DockerEngine: docker build (generated Dockerfile)
    DockerEngine-->>Docker: deps_image tag
    Docker-->>Runner: deps_image

    Note over Runner: Execute enabled rules (in order)
    loop for each enabled rule
        Runner->>Runner: _load_rule_module(rule_name)
        Runner->>Rule: Rule(config).execute(artifact_info)

        alt Rule is containerized (build_imports, unit_tests, security_*)
            Rule->>Docker: run_command(image=deps_image, command=[...])
            Docker->>DockerEngine: docker run ... -v project:/workspace
            DockerEngine-->>Docker: stdout/stderr/exit_code
            Docker-->>Rule: CompletedProcess
            Rule-->>Runner: pass/fail + details
        else Rule is local static analysis (policy)
            Rule-->>Runner: pass/fail + details
        end
    end

    Runner-->>CLI: EvaluationResult (results.json)
    CLI-->>User: summary + exit code
```

### Notes
- The **deps image** is built a single time from the contract’s `Environment` and `project.python_dependencies`.
- Each docker-based rule runs inside a container using that pre-built deps image.
- The `policy` rule is static analysis and runs locally (no container required).
