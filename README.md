# AgentRL

Harness Operating System for Agents.

AgentRL is a local-first systems layer for defining, evaluating, optimizing, versioning, and deploying agent harnesses through one interface. It is not an orchestration framework or an RL framework. RL, prompt optimization, skill optimization, memory optimization, and preference learning are implementation details behind the harness abstraction.

## Quick start

```bash
pip install -e .
agentrl init my-agent-system
cd my-agent-system
agentrl compile
agentrl train
agentrl evaluate
agentrl deploy
```

## Python API

```python
from agentrl import Project

project = Project("./my-agent-system")
project.compile()
project.train(strategy="verification")
project.evaluate()
project.auto_harness()
project.deploy()
```

## Repo2RLEnv boundary

Repo2RLEnv owns repository-to-verifiable-task synthesis. AgentRL consumes those outputs as coding tasks:

```python
from agentrl import Project
from agentrl.adapters import Repo2RLEnvAdapter

project = Project.init("./coding-agent")
source = Repo2RLEnvAdapter.from_repo(repo="pallets/click", pipeline="pr_runtime", limit=10)
project.harness("coding").add_tasks(source.to_taskset())
project.compile()
project.train(strategy="verification")
project.evaluate()
```

Clean boundary:

```text
Repo2RLEnv: repo → verifiable coding RL tasks
AgentRL: tasks + harness → evaluate, optimize, version, deploy
```

## MVP features

- Project abstraction
- Harness compilation
- TaskSet, RewardSpec, EvaluationResult schemas
- Local version registry with list/diff/rollback
- CLI commands: init, compile, train, evaluate, deploy, evolve, auto-harness, run-goal, version
- Built-in harnesses: coding, rag, tool_use
- Repo2RLEnvAdapter for Harbor-style coding tasks
- Evaluation engine with JSONL traces
- Basic self-evolution and auto-harness candidate promotion/archive
- Local deployment artifacts

## Bloat control

Public top-level ideas stay limited to Project, Harness, Memory, Skills, Version Registry, Observability, Deployment, Goal Workflows, and Auto-Harness. Advanced methods such as RLVR, DPO, GEPA, SkillOpt, TRL, Ray, and Verifiers remain backend integrations or implementation details.

## License

Apache-2.0
