from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .harness import Harness
from .models import RewardSpec, Task, TaskSet, stable_hash


@dataclass(frozen=True)
class HarnessComponent:
    """A reusable harness component attached to a targeted agent role."""

    name: str
    kind: str
    purpose: str
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TargetedAgentHarness:
    """AgentRL lifecycle declaration for one targeted agent role.

    Campaigns composes these as employed agents. AgentRL owns whether the harness is
    evaluated, evolved, versioned, and deployable.
    """

    agent_name: str
    role: str
    objective: str
    components: tuple[HarnessComponent, ...]
    harness: Harness

    @classmethod
    def create(
        cls,
        agent_name: str,
        role: str,
        objective: str,
        components: list[str] | tuple[str, ...] | None = None,
    ) -> "TargetedAgentHarness":
        component_names = tuple(components or infer_components(role=role, objective=objective))
        attached = tuple(component_for(name, role=role, objective=objective) for name in component_names)
        harness_name = f"{slugify(agent_name)}-harness"
        harness = Harness(
            name=harness_name,
            kind="targeted_agent",
            goal=objective,
            tools=sorted({tool for component in attached for tool in component.config.get("tools", [])}),
            rewards=[
                RewardSpec(name="evidence_quality", kind="review", weights={"success": 1.0}),
                RewardSpec(name="constraint_compliance", kind="verification", weights={"success": 1.0}),
                RewardSpec(name="traceability", kind="observability", weights={"success": 1.0}),
            ],
            prompts={
                "system": (
                    f"You are {agent_name}, a targeted {role} agent. Pursue the objective, "
                    "record decisions, cite evidence, respect constraints, and produce traceable work for final human review."
                )
            },
            memory_policy={
                "episodic": True,
                "semantic": True,
                "decision_log": True,
                "trace_retention": "campaign_lifetime",
            },
            metadata={
                "agent_name": agent_name,
                "role": role,
                "objective": objective,
                "components": [component.to_dict() for component in attached],
                "accountability": "ultimate_human_review",
            },
        )
        harness.add_tasks(
            TaskSet(
                name=f"{slugify(agent_name)}_readiness",
                provenance={"source": "targeted_agent_harness"},
                tasks=[
                    Task(
                        id=f"readiness-{stable_hash((agent_name, role, objective))[:8]}",
                        description=f"Verify {agent_name} can produce accountable {role} campaign work.",
                        kind="targeted_agent_readiness",
                        input={"objective": objective, "role": role},
                        expected={"expected_answer": "ready"},
                    )
                ],
            )
        )
        return cls(agent_name=agent_name, role=role, objective=objective, components=attached, harness=harness)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "objective": self.objective,
            "components": [component.to_dict() for component in self.components],
            "harness": self.harness.to_dict(),
        }


def slugify(value: str) -> str:
    return "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def infer_components(role: str, objective: str) -> tuple[str, ...]:
    text = f"{role} {objective}".lower()
    components = ["memory", "trace", "decision_log", "evaluation", "tool_use"]
    if any(token in text for token in ("research", "market", "rag", "knowledge", "seo")):
        components.append("rag")
    if any(token in text for token in ("outreach", "email", "ads", "seo", "marketing", "campaign")):
        components.append("approval_gate")
    if any(token in text for token in ("contract", "outsource", "worker", "parallel")):
        components.append("contracting")
    return tuple(dict.fromkeys(components))


def component_for(name: str, role: str, objective: str) -> HarnessComponent:
    catalog: dict[str, HarnessComponent] = {
        "memory": HarnessComponent("memory", "state", "Retain campaign context, learnings, and user constraints."),
        "trace": HarnessComponent("trace", "observability", "Record auditable execution traces for performance review."),
        "decision_log": HarnessComponent("decision_log", "accountability", "Capture decisions, rationale, evidence, risk, and approval needs."),
        "evaluation": HarnessComponent("evaluation", "lifecycle", "Score work quality before promotion or deployment."),
        "tool_use": HarnessComponent("tool_use", "capability", "Permit tool-mediated work with explicit trace records.", {"tools": ["web", "files", "terminal"]}),
        "rag": HarnessComponent("rag", "knowledge", "Ground research and recommendations in retrieved evidence.", {"tools": ["retrieval", "citation"]}),
        "approval_gate": HarnessComponent("approval_gate", "safety", "Require human approval for spend, outreach, publishing, or irreversible actions."),
        "contracting": HarnessComponent("contracting", "delegation", "Allow the employed agent to outsource bounded work to contract agents."),
    }
    if name not in catalog:
        return HarnessComponent(name, "custom", f"Custom component for {role}: {objective}")
    return catalog[name]
