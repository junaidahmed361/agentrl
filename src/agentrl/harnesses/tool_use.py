from __future__ import annotations

from agentrl.harness import Harness
from agentrl.models import RewardSpec, Task, TaskSet


class ToolUseHarness(Harness):
    def __init__(self) -> None:
        super().__init__(
            name="tool_use",
            kind="tool_use",
            goal="Select and call tools safely for goal-directed tasks.",
            tools=["calculator", "filesystem", "http"],
            rewards=[RewardSpec(name="tool_success", kind="optimization", weights={"success": 1.0})],
            prompts={"system": "Choose the smallest safe tool call and record inputs and outputs."},
        )
        self.add_tasks(TaskSet(
            name="tool_use_smoke",
            tasks=[Task(id="tool-smoke", description="Select calculator for arithmetic", kind="tool_use", input={"tool_call": "calculator.add"}, expected={"tool_call": "calculator.add"})],
            provenance={"source": "builtin"},
        ))
