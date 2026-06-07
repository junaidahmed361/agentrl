# AgentRL Implementation Plan

## MVP implemented in this repository

1. Core SDK: Project, Harness, Task, TaskSet, RewardSpec, EvaluationResult.
2. Core harnesses: Coding, RAG, Tool Use.
3. Version control: local registry, list, diff, rollback.
4. Self-evolution: prompt/skill/memory candidate generation, replay evaluation, promotion/archive.
5. Observability: JSONL traces and evaluation report.
6. Deployment: local deployment artifacts referencing versioned harnesses.
7. Repo2RLEnvAdapter: imports generated tasks into CodingHarness without reimplementing Repo2RLEnv synthesis.
8. OpenHarnessAdapter: registers external agent runtimes and imports execution traces without reimplementing agent loops, tools, MCP, permissions, memory execution, or subagents.

## Acceptance gates

```bash
pytest -q
agentrl init my-project
cd my-project
agentrl compile
agentrl train
agentrl evaluate
agentrl deploy
```

## Future work

- Docker, canary, blue/green deployment adapters.
- Hosted registry as optional service.
- External backend adapters for TRL, Ray, Verifiers, Atropos, LangGraph, Hermes, OpenHarness, and OpenClaw.
- Observability Studio UI.
