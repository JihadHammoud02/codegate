# `codegate/engine/`

Evaluation orchestration and execution.

## Key modules

- `runner.py` — the main orchestrator:
  - reads config from the contract
  - builds the Docker dependency image once
  - loads and runs each enabled rule
  - aggregates results into an `EvaluationResult`

- `docker_runner.py` — Docker utility layer:
  - builds the dependency image (runtime + system deps + python deps)
  - runs commands in containers with the right mounts and sandbox settings

- `result.py` — data structures for results (`RuleResult`, `EvaluationResult`)
