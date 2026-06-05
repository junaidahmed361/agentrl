from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from .models import Task, TaskSet, ensure_dir, stable_hash, utc_now
from .project import Project


@dataclass(frozen=True)
class RouteDecision:
    harness: str
    reason: str


class LocalAgentOS:
    """Small local CLI runtime that dogfoods AgentRL's harness lifecycle.

    This is intentionally not a competing agent runtime. It is a deterministic,
    local-first demo shell that shows how a Hermes-style agent surface can sit on
    top of Project, Harness, evaluation traces, memory, versioning, and local
    deployment records.
    """

    def __init__(self, project: Project):
        self.project = project
        self.session_dir = ensure_dir(project.root / ".agentrl" / "agent_os")
        self.memory_path = self.session_dir / "memory.jsonl"
        self.session_path = self.session_dir / "sessions.jsonl"

    def overview(self) -> dict[str, Any]:
        return {
            "project": str(self.project.root),
            "system": "local-agent-os",
            "agents": [
                {"name": "router_agent", "role": "routes goals to a harness"},
                {"name": "coding_agent", "role": "handles verifiable code tasks", "harness": "coding"},
                {"name": "rag_agent", "role": "handles grounded answer tasks", "harness": "rag"},
                {"name": "tool_agent", "role": "handles tool-selection tasks", "harness": "tool_use"},
            ],
            "harnesses": {name: harness.to_dict() for name, harness in self.project.harnesses.items()},
            "commands": ["/help", "/harnesses", "/memory", "/evaluate", "/deploy", "/versions", "/exit"],
        }

    def route(self, goal: str) -> RouteDecision:
        text = goal.lower()
        if any(token in text for token in ["code", "test", "bug", "repo", "fix", "pytest", "file", "function"]):
            return RouteDecision("coding", "goal mentions code/repo/test-style work")
        if any(token in text for token in ["search", "docs", "rag", "cite", "citation", "answer", "knowledge"]):
            return RouteDecision("rag", "goal mentions retrieval or grounded answering")
        if any(token in text for token in ["tool", "api", "call", "calculate", "terminal", "shell", "http"]):
            return RouteDecision("tool_use", "goal mentions tool selection or tool calls")
        return RouteDecision("coding", "default local-agent-os route for open-ended goals")

    def run_goal(self, goal: str) -> dict[str, Any]:
        decision = self.route(goal)
        harness = self.project.harness(decision.harness)
        task_id = f"local-goal-{stable_hash({'goal': goal, 'harness': decision.harness})[:8]}"
        task = self._task_for_goal(task_id, goal, decision.harness)
        harness.add_tasks(TaskSet(
            name="local_agent_os_goals",
            tasks=[task],
            provenance={"source": "agentrl.local_agent_os", "created_at": utc_now()},
        ))
        result = harness.evaluate(self.project.root, ensure_dir(self.project.root / ".agentrl" / "traces"))
        memory = {
            "at": utc_now(),
            "goal": goal,
            "harness": decision.harness,
            "route_reason": decision.reason,
            "task_id": task_id,
            "pass_rate": result.pass_rate,
            "trace_path": result.trace_path,
        }
        self._append_jsonl(self.memory_path, memory)
        response = {
            "goal": goal,
            "router": decision.__dict__,
            "selected_harness": decision.harness,
            "task": task.to_dict(),
            "evaluation": result.to_dict(),
            "memory_recorded": str(self.memory_path),
            "next_steps": [
                "Inspect the trace_path for the recorded trajectory.",
                "Run `agentrl evaluate` to compare all harnesses.",
                "Run `agentrl auto-harness --mode adaptive` to create an improvement candidate.",
                "Run `agentrl deploy` to publish a local deployment record once evaluations pass.",
            ],
        }
        self._append_jsonl(self.session_path, response)
        return response

    def evaluate(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.project.evaluate()]

    def deploy(self) -> dict[str, Any]:
        return self.project.deploy(strategy="local")

    def versions(self) -> list[dict[str, Any]]:
        return self.project.registry.list()

    def memory(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self.memory_path.exists():
            return []
        lines = self.memory_path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]

    def _task_for_goal(self, task_id: str, goal: str, harness_name: str) -> Task:
        if harness_name == "coding":
            return Task(
                id=task_id,
                description=goal,
                kind="coding",
                input={"goal": goal},
                expected={"command": "python3 -c 'print(\"local coding harness ready\")'"},
                metadata={"source": "local_agent_os", "sandbox": {"path": str(self.project.root)}},
                reward="pytest",
            )
        if harness_name == "rag":
            answer = "AgentRL turns agents, repos, tools, or runtimes into local harnesses."
            return Task(
                id=task_id,
                description=goal,
                kind="rag",
                input={"goal": goal, "answer": answer},
                expected={"expected_answer": answer},
                metadata={"source": "local_agent_os", "citations": ["README.md"]},
            )
        return Task(
            id=task_id,
            description=goal,
            kind="tool_use",
            input={"goal": goal, "tool_call": "terminal.run"},
            expected={"tool_call": "terminal.run"},
            metadata={"source": "local_agent_os", "approval": "local_safe_demo"},
        )

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")


def run_repl(project: Project) -> int:
    os = LocalAgentOS(project)
    print("AgentRL local-agent-os")
    print("Hermes-style local harness shell. Type /help for commands, /exit to quit.")
    while True:
        try:
            raw = input("agentrl> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not raw:
            continue
        if raw in {"/exit", "/quit"}:
            return 0
        if raw == "/help":
            print(json.dumps(os.overview()["commands"], indent=2))
        elif raw == "/harnesses":
            print(json.dumps(os.overview()["harnesses"], indent=2))
        elif raw == "/memory":
            print(json.dumps(os.memory(), indent=2))
        elif raw == "/evaluate":
            print(json.dumps(os.evaluate(), indent=2))
        elif raw == "/deploy":
            print(json.dumps(os.deploy(), indent=2))
        elif raw == "/versions":
            print(json.dumps(os.versions(), indent=2))
        else:
            print(json.dumps(os.run_goal(raw), indent=2))
    return 0
