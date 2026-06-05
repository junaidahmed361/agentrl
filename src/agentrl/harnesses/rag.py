from __future__ import annotations

from agentrl.harness import Harness
from agentrl.models import RewardSpec, Task, TaskSet


class RAGHarness(Harness):
    def __init__(self) -> None:
        super().__init__(
            name="rag",
            kind="rag",
            goal="Answer retrieval tasks with grounded citations and hallucination control.",
            tools=["retriever"],
            rewards=[RewardSpec(name="grounded_answer", kind="preference", weights={"success": 1.0})],
            prompts={"system": "Answer only from retrieved context and include citations."},
            metadata={"reward_dimensions": {"citation_quality": 0.5, "hallucination_penalty": 0.4}},
        )
        self.add_tasks(TaskSet(
            name="rag_smoke",
            tasks=[Task(id="rag-smoke", description="Answer from supplied context", kind="rag", input={"answer": "AgentRL is a Harness Operating System."}, expected={"expected_answer": "AgentRL is a Harness Operating System."})],
            provenance={"source": "builtin"},
        ))
