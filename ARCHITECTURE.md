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
- TargetedAgentHarness: role-specific harness declaration with inferred components for employed campaign agents.
- Version Registry: local `.agentrl/registry` artifact store.
- Evaluation: runs task verification and emits metrics plus JSONL traces.
- Self-Evolution: creates bounded prompt/skill/memory candidates, evaluates them, promotes winners, archives rejected candidates.
- Deployment: local deployment records referencing versioned harness artifacts.

## Repo2RLEnv Adapter

The adapter imports Repo2RLEnv or Harbor-compatible task outputs into `TaskSet`. It preserves provenance, content hashes, sandbox metadata, and executable verification commands. It intentionally does not synthesize repository tasks itself.

## OpenHarness Adapter

OpenHarness is treated as a runtime adapter, not as a feature list for AgentRL to reimplement.

```text
OpenHarness: goal/task → execution trajectory
AgentRL: execution trajectory → evaluation → evolution → versioning → deployment
```

The adapter can register an OpenHarness runtime boundary with `Project.attach_runtime(...)` and import OpenHarness-style traces into `TaskSet` objects. Runtime concerns such as tools, MCP, permissions, memory execution, skills loading, subagents, hooks, context compression, and the agent loop remain OpenHarness responsibilities.

## Layering

CampaignOS / Campaigns can sit above AgentRL. In that relationship, a user first creates a targeted AgentRL harness such as `Market Researcher`; Campaigns later employs that harness in a campaign fleet and may let the employed agent contract short-term workers. AgentRL remains responsible for the employed agent's lifecycle artifacts: components, evals, traces, self-evolution candidates, versions, deployment, and rollback.

```text
Campaigns
  goal → organization → employed agents → contract agents → final review

AgentRL
  targeted agent harness → evaluate → evolve → version → deploy/rollback

Runtime
  task or goal → execution trajectory
```

## Design constraints

- No competing workflow engine.
- No agent graph runtime as a public API.
- No protocol framework or memory framework as top-level concepts.
- RL, GEPA, SkillOpt, DPO, TRL, Ray, Verifiers, and Atropos remain implementation details or adapters.
