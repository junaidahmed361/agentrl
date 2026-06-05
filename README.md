# AgentRL

<p align="center">
  <img src="https://raw.githubusercontent.com/junaidahmed361/agentrl/main/assets/agentrl-header.png" alt="AgentRL - Harness Operating System for Agents" width="100%">
</p>

[![PyPI version](https://badge.fury.io/py/agentrl-os.svg)](https://pypi.org/project/agentrl-os/)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://pypi.org/project/agentrl-os/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/junaidahmed361/agentrl/blob/main/LICENSE)
[![CI](https://github.com/junaidahmed361/agentrl/actions/workflows/ci.yml/badge.svg)](https://github.com/junaidahmed361/agentrl/actions/workflows/ci.yml)
[![Package check](https://github.com/junaidahmed361/agentrl/actions/workflows/package.yml/badge.svg)](https://github.com/junaidahmed361/agentrl/actions/workflows/package.yml)

Local-first Harness Operating System for defining, evaluating, evolving, versioning, and deploying agent harnesses.

Bring your own agent, repo, tools, or runtime. AgentRL turns them into harnesses you can evaluate, improve, version, and deploy locally.

## Packages

Install from PyPI:

```bash
pip install agentrl-os
```

Run from GitHub Container Registry:

```bash
docker pull ghcr.io/junaidahmed361/agentrl:latest
docker run --rm ghcr.io/junaidahmed361/agentrl:latest --version
```

GitHub package: `ghcr.io/junaidahmed361/agentrl`

Package name: `agentrl-os`

Import package: `agentrl`

CLI command: `agentrl`

AgentRL is a systems layer for defining, evaluating, evolving, versioning, and deploying agent harnesses through one unified interface. It standardizes how agent systems are tested and improved over time without forcing teams to rebuild task formats, reward schemas, trajectory traces, registries, and local deployment plumbing from scratch.

AgentRL is not an orchestration framework and not primarily an RL framework. RL, prompt optimization, skill optimization, memory optimization, preference learning, and tool optimization are implementation details behind the harness abstraction.

## Why AgentRL exists

Agentic systems are becoming easier to prototype and harder to operate.

A team can assemble a capable agent from a model, a prompt, tools, memory, an orchestration library, and a few eval scripts. The hard part starts after the demo:

```text
How are tasks represented?
How are rewards represented?
How are evaluation results compared over time?
How are trajectories stored and replayed?
How are harness changes versioned?
How do you know a prompt, skill, tool policy, or memory policy actually improved behavior?
How do you safely deploy a new behavior and roll it back?
```

Most agent projects answer these questions with ad-hoc glue code. That glue code becomes the real operating system for the agent, but it is rarely standardized, versioned, or portable.

AgentRL exists to make that systems layer explicit.

The goal is to make building, improving, and operating agent harnesses feel closer to using scikit-learn-style project primitives:

```python
from agentrl import Project

project = Project("./my-agent-system")
project.compile()
project.train(strategy="verification")
project.evaluate()
project.auto_harness()
project.deploy()
```

## The gap AgentRL fills

The ecosystem already has strong tools, but they solve different parts of the lifecycle:

- LangGraph helps build stateful agent orchestration graphs.
- TRL helps train models with reinforcement learning and preference methods.
- Ray helps scale distributed execution.
- Verifiers and RLVR-style systems help score verifiable tasks.
- Atropos-style systems help collect rollouts and trajectories.
- Repo2RLEnv/Harbor-style systems turn repositories into verifiable coding tasks.
- Evaluation frameworks help run benchmark suites.

AgentRL is the layer above those pieces:

```text
tasks + harness + rewards + evaluation + traces + versions + deployment
```

It gives those pieces a common operating model so teams can move from experiments to repeatable harness evolution without locking into a single runtime or training method.

## What AgentRL is and is not

AgentRL is a Harness Operating System.

It owns:

- Project layout
- Harness definitions
- Task and reward schemas
- Evaluation records
- Trajectory/trace observability
- Local version registry
- Self-evolution candidate management
- Local deployment records
- Adapter boundaries to external systems

It does not try to replace:

- agent runtimes
- graph orchestration frameworks
- RL training libraries
- distributed compute systems
- repository-to-task synthesis pipelines
- hosted experiment platforms

Those are integrations or backends. AgentRL standardizes the harness lifecycle around them.

## Differentiation from existing tools

### AgentRL vs LangGraph

LangGraph is for orchestrating stateful agent workflows.

AgentRL is for defining, evaluating, evolving, versioning, and deploying the harnesses those workflows run inside.

A LangGraph app can be wrapped by an AgentRL harness. AgentRL should not become a competing graph runtime.

```text
LangGraph: how should the agent transition between steps?
AgentRL: how is this behavior evaluated, improved, versioned, and deployed?
```

### AgentRL vs TRL/RL libraries

TRL and similar libraries help train models.

AgentRL starts before and around training: task schemas, reward specs, evaluations, traces, versioning, and deployment. Training is one possible optimization backend, not the identity of the project.

```text
TRL: optimize model weights.
AgentRL: operate harnesses; use training only when cheaper optimizations are insufficient.
```

AgentRL’s preferred improvement order is intentionally practical:

```text
prompts → skills → memory policies → routing → tools → fine-tuning → RL
```

### AgentRL vs eval frameworks

Eval frameworks usually run tests and produce scores.

AgentRL includes evaluation, but connects it to harness compilation, candidate evolution, trace replay, version registry, deployment preflight checks, and rollback.

```text
Eval framework: did this system pass a test?
AgentRL: should this harness change be promoted and deployed?
```

### AgentRL vs Repo2RLEnv / Harbor

Repo2RLEnv/Harbor-style systems generate verifiable coding tasks from repositories.

AgentRL does not reimplement that synthesis. It imports those tasks into `CodingHarness` using `Repo2RLEnvAdapter`, preserving provenance, content hashes, sandbox metadata, and executable verification rewards.

```text
Repo2RLEnv: repo → verifiable coding tasks
AgentRL: tasks + harness → evaluate, optimize, version, deploy
```

If Repo2RLEnv output is unavailable or invalid, AgentRL records provenance errors and imports no fabricated passing tasks.

### AgentRL vs hosted experiment platforms

AgentRL is local-first. The MVP works without a hosted service:

- harness compilation
- local registry
- local traces
- local evaluation
- local self-evolution candidates
- local deployment records

Hosted registries, managed evals, GPU training, or enterprise governance can exist later as optional services, not prerequisites.

## Research and library lineage

AgentRL is designed to sit on top of, or interoperate with, research and libraries such as:

- RLVR / execution rewards for verifiable tasks
- DPO and preference learning for subjective tasks
- GEPA-style reflective prompt evolution
- SkillOpt-style skill evolution
- learned reward models and LLM judges
- TRL for training backends
- Ray for distributed execution
- LangGraph for orchestration backends
- Verifiers for executable reward environments
- Atropos-style trajectory collection
- Repo2RLEnv / Harbor for repo-derived coding tasks

These remain implementation details. AgentRL’s public abstraction stays centered on `Project` and `Harness`.

## Install

```bash
pip install agentrl-os
```

For local development:

```bash
git clone https://github.com/junaidahmed361/agentrl.git
cd agentrl
uv sync --extra dev
uv run pytest -q
```

## Quick start

```bash
agentrl init my-agent-system
cd my-agent-system
agentrl compile
agentrl train
agentrl evaluate
agentrl deploy
```

## Example demo

For a local Hermes-style agent replication demo, see:

[examples/local-hermes-agent-os.md](examples/local-hermes-agent-os.md)

The demo shows how AgentRL can represent a local agent OS with router, coding, RAG, tool-use, memory, skills, registry, traces, and local deployment while keeping Hermes-style execution as a harness capability rather than a competing runtime.

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

## Core operating model

```text
Project
├── Harnesses
│   ├── Tasks
│   ├── Rewards
│   ├── Evaluations
│   ├── Policies
│   └── Goal Workflows
├── Memory
├── Skills
├── Version Registry
├── Observability
└── Deployment
```

Public top-level concepts stay intentionally small:

- Project
- Harness
- Memory
- Skills
- Version Registry
- Observability
- Deployment
- Goal Workflows
- Auto-Harness

Advanced methods such as RLVR, DPO, GEPA, SkillOpt, TRL, Ray, LangGraph, Verifiers, and Atropos are adapters or backend implementation details.

## Built-in harnesses

- `coding`: verifiable coding tasks using filesystem/terminal evidence
- `rag`: retrieval-grounded question answering with citation/hallucination reward dimensions
- `tool_use`: safe tool-selection and tool-call evaluation

## Repo2RLEnv adapter

```python
from agentrl import Project
from agentrl.adapters import Repo2RLEnvAdapter

project = Project.init("./coding-agent")
source = Repo2RLEnvAdapter.from_repo(
    repo="pallets/click",
    pipeline="pr_runtime",
    limit=10,
)
project.harness("coding").add_tasks(source.to_taskset())
project.compile()
project.train(strategy="verification")
project.evaluate()
```

The adapter maps Repo2RLEnv/Harbor-style metadata into AgentRL `TaskSet` objects and attaches executable verification rewards to the coding harness.

## CLI

```bash
agentrl --version
agentrl init my-project
agentrl compile
agentrl train --strategy verification
agentrl evaluate
agentrl evolve --targets prompts,skills,memory
agentrl auto-harness --mode static
agentrl run-goal "Fix the failing login test."
agentrl deploy
agentrl version list
agentrl version diff <left-version-id> <right-version-id>
agentrl version rollback <version-id>
```

## Local-first artifacts

AgentRL stores project-local state under `.agentrl/`:

```text
.agentrl/
├── compiled/          # compiled harness specs
├── registry/          # local version registry artifacts
├── traces/            # JSONL evaluation traces
├── candidates/        # promoted self-evolution candidates
├── rejected/          # rejected candidates
└── deployments/local/ # local deployment records
```

## MVP features

- Project abstraction
- Harness compilation
- TaskSet, RewardSpec, EvaluationResult schemas
- Local version registry with list/diff/rollback
- Built-in coding, RAG, and tool-use harnesses
- Repo2RLEnvAdapter for Harbor-style coding tasks
- Evaluation engine with JSONL traces
- Basic self-evolution and auto-harness candidate promotion/archive
- Local deployment artifacts with evaluation preflight gating
- Typed Python package and console script

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run python -m build
uv run twine check dist/*
```

## License

Apache-2.0. See [LICENSE](LICENSE).
