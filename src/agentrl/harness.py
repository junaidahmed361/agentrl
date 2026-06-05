from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import subprocess

from .models import EvaluationResult, RewardSpec, Task, TaskSet, utc_now


@dataclass
class Harness:
    name: str
    kind: str
    goal: str
    tools: list[str] = field(default_factory=list)
    rewards: list[RewardSpec] = field(default_factory=list)
    tasksets: list[TaskSet] = field(default_factory=list)
    prompts: dict[str, str] = field(default_factory=dict)
    skills: dict[str, str] = field(default_factory=dict)
    memory_policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def define(cls, goal: str, tools: list[str] | None = None, success: list[str] | None = None, name: str = "custom") -> "Harness":
        rewards = [RewardSpec(name=s, kind="verification") for s in (success or ["success"])]
        return cls(name=name, kind="custom", goal=goal, tools=tools or [], rewards=rewards)

    def add_tasks(self, taskset: TaskSet) -> None:
        self.tasksets.append(taskset)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "goal": self.goal,
            "tools": self.tools,
            "rewards": [r.to_dict() for r in self.rewards],
            "tasksets": [ts.to_dict() for ts in self.tasksets],
            "prompts": self.prompts,
            "skills": self.skills,
            "memory_policy": self.memory_policy,
            "metadata": self.metadata,
        }

    def compile(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.name}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def evaluate_task(self, task: Task, project_root: Path) -> dict[str, Any]:
        if task.reward == "pytest" or task.expected.get("command"):
            command = task.expected.get("command", "pytest -q")
            cwd = Path(task.metadata.get("sandbox", {}).get("path", project_root))
            timeout = task.expected.get("timeout", 120)
            try:
                proc = subprocess.run(command, shell=True, cwd=cwd, text=True, capture_output=True, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                return {
                    "success": False,
                    "stdout": (exc.stdout or "")[-4000:],
                    "stderr": (exc.stderr or f"command timed out after {timeout} seconds")[-4000:],
                    "returncode": None,
                    "error": "timeout",
                }
            except OSError as exc:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": str(exc)[-4000:],
                    "returncode": None,
                    "error": exc.__class__.__name__,
                }
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
                "returncode": proc.returncode,
            }
        if "expected_answer" in task.expected:
            return {"success": task.input.get("answer") == task.expected["expected_answer"]}
        if "tool_call" in task.expected:
            return {"success": task.input.get("tool_call") == task.expected["tool_call"]}
        return {"success": False, "error": "unverifiable_task", "stderr": "Task has no executable command or expected assertion."}

    def evaluate(self, project_root: Path, trace_dir: Path) -> EvaluationResult:
        trace_dir.mkdir(parents=True, exist_ok=True)
        rewards: list[float] = []
        failures: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        reward_spec = self.rewards[0] if self.rewards else RewardSpec(name="success")
        for taskset in self.tasksets:
            for task in taskset.tasks:
                result = self.evaluate_task(task, project_root)
                score = reward_spec.score(task, result)
                rewards.append(score)
                event = {"at": utc_now(), "harness": self.name, "task": task.to_dict(), "result": result, "reward": score}
                events.append(event)
                if score <= 0:
                    failures.append({"task_id": task.id, "description": task.description, "result": result})
        average = sum(rewards) / len(rewards) if rewards else 0.0
        pass_rate = sum(1 for r in rewards if r > 0) / len(rewards) if rewards else 0.0
        trace_path = trace_dir / f"{self.name}-{utc_now().replace(':', '-')}.jsonl"
        trace_path.write_text("\n".join(json.dumps(e, sort_keys=True) for e in events), encoding="utf-8")
        return EvaluationResult(self.name, len(rewards), average, pass_rate, rewards, failures, str(trace_path))
