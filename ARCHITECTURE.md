# AgentRL Architecture

AgentRL is a local-first Harness Operating System.

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

## Core components

- Project: root abstraction and lifecycle facade.
- Harness: task, reward, prompt, skill, memory policy, tool, and evaluation unit.
- Version Registry: local `.agentrl/registry` artifact store.
- Evaluation: runs task verification and emits metrics plus JSONL traces.
- Self-Evolution: creates bounded prompt/skill/memory candidates, evaluates them, promotes winners, archives rejected candidates.
- Deployment: local deployment records referencing versioned harness artifacts.

## Repo2RLEnv Adapter

The adapter imports Repo2RLEnv or Harbor-compatible task outputs into `TaskSet`. It preserves provenance, content hashes, sandbox metadata, and executable verification commands. It intentionally does not synthesize repository tasks itself.

## Design constraints

- No competing workflow engine.
- No agent graph runtime as a public API.
- No protocol framework or memory framework as top-level concepts.
- RL, GEPA, SkillOpt, DPO, TRL, Ray, Verifiers, and Atropos remain implementation details or adapters.
