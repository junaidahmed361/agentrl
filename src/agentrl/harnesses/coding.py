from __future__ import annotations

from agentrl.harness import Harness
from agentrl.models import RewardSpec, Task, TaskSet


class CodingHarness(Harness):
    def __init__(self) -> None:
        super().__init__(
            name="coding",
            kind="coding",
            goal="Solve verifiable coding tasks with filesystem and terminal evidence.",
            tools=["filesystem", "terminal"],
            rewards=[RewardSpec(name="tests_pass", kind="verification", weights={"success": 1.0})],
            prompts={"system": "Modify code minimally, run verification, and preserve provenance."},
        )
        self.add_tasks(TaskSet(
            name="coding_smoke",
            tasks=[Task(id="coding-smoke", description="Default coding harness smoke task", kind="coding", expected={"command": "python3 -c 'print(1)'"}, reward="pytest")],
            provenance={"source": "builtin"},
        ))
