# Local Hermes-Style Agent OS Demo

This demo shows how AgentRL can model a local Hermes-style agent system without becoming an agent runtime itself.

The goal is to replicate the operating pattern of a local personal agent system:

```text
Router Agent
├── Coding Agent
├── RAG Agent
├── Tool Agent
├── Memory System
├── Skill System
├── Harness Registry
└── Observability Traces
```

AgentRL treats each behavior as a harness that can be compiled, evaluated, evolved, versioned, and deployed locally.

## Run the demo

Fast path:

```bash
pip install agentrl-os
agentrl demo local-agent-os --path local-hermes-agent-os --goal "Fix a failing pytest in this repo"
cd local-hermes-agent-os
agentrl agent-os
```

That one `agentrl demo local-agent-os` command initializes the template, compiles harness specs, routes a sample goal, writes traces/memory, runs evaluation, creates an adaptive auto-harness candidate, and writes a local deployment record.

Manual path, if you want to run each lifecycle step yourself:

```bash
pip install agentrl-os
agentrl init local-hermes-agent-os --template local-agent-os
cd local-hermes-agent-os
agentrl compile
agentrl agent-os --overview
agentrl agent-os --goal "Fix a failing pytest in this repo"
agentrl evaluate
agentrl auto-harness --mode adaptive
agentrl deploy
agentrl version list
```

You can also inspect a demo project without changing directories:

```bash
agentrl agent-os --project local-hermes-agent-os --memory
agentrl agent-os --project local-hermes-agent-os --overview
```

## What this creates

The generated project includes the three MVP harnesses:

- `coding`: local coding tasks with executable verification rewards
- `rag`: retrieval-grounded answer tasks with citation/hallucination reward dimensions
- `tool_use`: safe tool-selection and tool-call tasks

AgentRL stores local operating artifacts in `.agentrl/`:

```text
.agentrl/
├── compiled/          # compiled harness specs
├── registry/          # local version registry artifacts
├── traces/            # JSONL evaluation traces
├── candidates/        # promoted self-evolution candidates
└── deployments/local/ # local deployment records
```

## Why this is Hermes-style, not a Hermes clone

Hermes is a local agent runtime with tools, memory, skills, gateway integrations, and operational workflows.

AgentRL does not replace Hermes. Instead, it provides the harness operating layer around a Hermes-like system:

```text
Hermes-style runtime: execute local agent workflows
AgentRL: evaluate, evolve, version, trace, and deploy harness behavior
```

A future adapter can wrap a real Hermes runtime as a harness backend while preserving the same AgentRL lifecycle:

```python
from agentrl import Project

project = Project("./local-hermes-agent-os")
project.compile()
project.evaluate()
project.auto_harness(mode="adaptive")
project.deploy()
```

## Acceptance checklist

After running the demo, verify:

```bash
agentrl evaluate
agentrl version list
ls .agentrl/traces
ls .agentrl/deployments/local
```

Expected result:

- coding, rag, and tool_use harnesses evaluate successfully
- JSONL traces are written locally
- version registry contains harness/evaluation/deployment records
- local deployment preflight passes
