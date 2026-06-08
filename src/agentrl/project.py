from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import yaml

from .agent_harness import TargetedAgentHarness
from .harness import Harness
from .harnesses import CodingHarness, RAGHarness, ToolUseHarness
from .models import EvaluationResult, RewardSpec, Task, TaskSet, ensure_dir, stable_hash, utc_now
from .registry import VersionRegistry


class Project:
    def __init__(self, path: str | Path):
        self.root = Path(path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.agentrl_dir = ensure_dir(self.root / ".agentrl")
        self.registry = VersionRegistry(self.root)
        self.harnesses: dict[str, Harness] = {}
        self.config_path = self.root / "agentrl.yaml"
        if self.config_path.exists():
            self._load_config()

    @classmethod
    def init(cls, path: str | Path, template: str = "default") -> "Project":
        project = cls(path)
        if not project.config_path.exists():
            config = cls._template_config(Path(path).name, template)
            project.config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        project.add_harness("coding")
        project.add_harness("rag")
        project.add_harness("tool_use")
        if template in {"local-agent-os", "local_hermes", "hermes"}:
            project._write_local_agent_os_readme()
        project._save_manifest()
        return project

    @staticmethod
    def _template_config(name: str, template: str) -> dict[str, Any]:
        base = {
            "system": {"name": name},
            "agents": [
                {"name": "coding_agent", "type": "coding"},
                {"name": "rag_agent", "type": "rag"},
                {"name": "tool_agent", "type": "tool_use"},
            ],
            "harnesses": ["coding", "rag", "tool_use"],
            "memory": {"episodic": True, "semantic": True, "skills": True},
            "deployment": {"strategy": "local"},
        }
        if template in {"local-agent-os", "local_hermes", "hermes"}:
            base["system"] |= {"template": "local-agent-os", "description": "Hermes-style local agent harness stack"}
            base["agents"] = [
                {"name": "router_agent", "type": "router", "routes_to": ["coding", "rag", "tool_use"]},
                {"name": "coding_agent", "type": "coding", "harness": "coding"},
                {"name": "rag_agent", "type": "rag", "harness": "rag"},
                {"name": "tool_agent", "type": "tool_use", "harness": "tool_use"},
            ]
            base["observability"] = {"traces": True, "local_memory_jsonl": True, "registry": True}
            base["deployment"] = {"strategy": "local", "approval": "evaluation_passes"}
        return base

    def _write_local_agent_os_readme(self) -> None:
        readme = self.root / "LOCAL_AGENT_OS.md"
        if readme.exists():
            return
        readme.write_text(
            "# Local Agent OS demo\n\n"
            "This project dogfoods AgentRL as a Hermes-style local harness stack.\n\n"
            "Run the one-command bootstrap from outside the project with:\n\n"
            "```bash\n"
            "agentrl demo local-agent-os --path local-agent-os --goal \"Fix a failing test in this repo\"\n"
            "```\n\n"
            "Then continue inside the project with:\n\n"
            "```bash\n"
            "agentrl agent-os --goal \"Fix a failing test in this repo\"\n"
            "agentrl agent-os\n"
            "```\n\n"
            "The shell includes a router agent plus coding, RAG, and tool-use harnesses. "
            "It records local JSONL memory, writes evaluation traces, registers versions, "
            "and creates local deployment records under `.agentrl/`.\n",
            encoding="utf-8",
        )

    def _load_config(self) -> None:
        config = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        for name in config.get("harnesses", []):
            self.add_harness(name)

    def _save_manifest(self) -> None:
        manifest = {"root": str(self.root), "harnesses": list(self.harnesses), "updated_at": utc_now()}
        (self.agentrl_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def add_harness(self, name: str, source: Any | None = None) -> Harness:
        if isinstance(name, Harness):
            harness = name
        elif name == "coding":
            harness = CodingHarness()
        elif name == "rag":
            harness = RAGHarness()
        elif name == "tool_use":
            harness = ToolUseHarness()
        else:
            harness = Harness(name=name, kind=name, goal=f"Run {name} tasks")
        if source is not None:
            harness.add_tasks(source.to_taskset() if hasattr(source, "to_taskset") else source)
        self.harnesses[harness.name] = harness
        self._save_manifest()
        return harness

    def harness(self, name: str) -> Harness:
        return self.harnesses[name]

    def create_agent_harness(
        self,
        agent_name: str,
        role: str,
        objective: str,
        components: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a targeted agent harness with inferred lifecycle components.

        This is the AgentRL-side primitive Campaigns consumes when a user decides
        to employ a targeted agent such as a market researcher.
        """

        targeted = TargetedAgentHarness.create(
            agent_name=agent_name,
            role=role,
            objective=objective,
            components=components,
        )
        self.harnesses[targeted.harness.name] = targeted.harness
        harness_dir = ensure_dir(self.root / ".agentrl" / "targeted_agents")
        path = harness_dir / f"{targeted.harness.name}.json"
        path.write_text(json.dumps(targeted.to_dict(), indent=2), encoding="utf-8")
        version = self.registry.register_file(
            path,
            entity=f"targeted_agent:{targeted.agent_name}",
            metadata={"role": role, "components": [component.name for component in targeted.components]},
        )
        self._save_manifest()
        return {"status": "created", "targeted_agent": targeted.to_dict(), "path": str(path), "version": version.to_dict()}

    def attach_runtime(self, runtime: Any, name: str | None = None) -> dict[str, Any]:
        """Register an execution runtime adapter without making AgentRL a runtime.

        Runtime adapters own goal -> execution. AgentRL stores their boundary,
        provenance, and imported artifacts so the project lifecycle can evaluate,
        evolve, version, and deploy behavior around them.
        """

        runtime_dir = ensure_dir(self.root / ".agentrl" / "runtimes")
        if hasattr(runtime, "to_runtime_record"):
            record = runtime.to_runtime_record()
        elif isinstance(runtime, dict):
            record = dict(runtime)
        else:
            record = {"adapter": type(runtime).__name__, "metadata": repr(runtime)}
        record.setdefault("name", name or record.get("adapter", "runtime"))
        record.setdefault("boundary", "Runtime executes goals; AgentRL manages lifecycle artifacts.")
        path = runtime_dir / f"{str(record['name']).replace('/', '-')}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        version = self.registry.register_file(path, entity=f"runtime:{record['name']}", metadata={"adapter": record.get("adapter")})
        return {"status": "attached", "runtime": record, "path": str(path), "version": version.to_dict()}

    def compile(self) -> list[dict[str, Any]]:
        compiled_dir = ensure_dir(self.root / ".agentrl" / "compiled")
        records = []
        for harness in self.harnesses.values():
            path = harness.compile(compiled_dir)
            records.append(self.registry.register_file(path, entity=f"harness:{harness.name}", metadata={"kind": harness.kind}).to_dict())
        return records

    def fit(self, X: Any | None = None, y: Any | None = None, strategy: str = "verification") -> "Project":
        """Scikit-learn-style lifecycle fit.

        `fit` optimizes harness artifacts and stores the candidate on `fit_result_`.
        AgentRL keeps this limited to harness lifecycle work; campaign autorun and
        dynamic organization loops belong in the Campaigns repo.
        """

        self.fit_result_ = self.train(strategy=strategy)
        return self

    def transform(self, X: Any | None = None) -> list[dict[str, Any]]:
        """Compile harness artifacts as the sklearn-style transform output."""

        return self.compile()

    def fit_transform(self, X: Any | None = None, y: Any | None = None, strategy: str = "verification") -> list[dict[str, Any]]:
        return self.fit(X=X, y=y, strategy=strategy).transform(X)

    def score(self, X: Any | None = None, y: Any | None = None) -> float:
        """Return average evaluation pass rate across project harnesses."""

        results = self.evaluate()
        if not results:
            return 0.0
        return sum(result.pass_rate for result in results) / len(results)

    def evaluate(self) -> list[EvaluationResult]:
        trace_dir = ensure_dir(self.root / ".agentrl" / "traces")
        results = [h.evaluate(self.root, trace_dir) for h in self.harnesses.values()]
        report = {"created_at": utc_now(), "results": [r.to_dict() for r in results]}
        report_path = self.root / ".agentrl" / "evaluation.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.registry.register_file(report_path, entity="evaluation", metadata={"harnesses": list(self.harnesses)})
        return results

    def train(self, strategy: str = "verification") -> dict[str, Any]:
        if strategy not in {"verification", "preference", "optimization", "simulation"}:
            raise ValueError(f"unsupported strategy: {strategy}")
        return self.evolve(targets=["prompts", "skills", "memory"], strategy=strategy)

    def evolve(self, targets: list[str] | None = None, strategy: str = "verification") -> dict[str, Any]:
        targets = targets or ["prompts", "skills", "memory"]
        before = self.evaluate()
        candidate = {"created_at": utc_now(), "strategy": strategy, "targets": targets, "changes": []}
        for harness in self.harnesses.values():
            if "prompts" in targets:
                old = harness.prompts.get("system", harness.goal)
                harness.prompts["system"] = old + "\nPrefer verifiable, concise actions and record evidence for each step."
                candidate["changes"].append({"harness": harness.name, "target": "prompts", "status": "candidate"})
            if "memory" in targets:
                harness.memory_policy.setdefault("compression", "summarize_on_trace_threshold")
            if "skills" in targets:
                harness.skills.setdefault("best", "Use validation feedback before promoting changes.")
        after = self.evaluate()
        after_score = sum(r.average_reward for r in after)
        before_score = sum(r.average_reward for r in before)
        after_has_failures = any(r.failures for r in after)
        promoted = after_score >= before_score and not after_has_failures
        candidate["promoted"] = promoted
        archive_dir = ensure_dir(self.root / ".agentrl" / ("candidates" if promoted else "rejected"))
        path = archive_dir / f"candidate-{stable_hash(candidate)[:8]}.json"
        path.write_text(json.dumps(candidate, indent=2), encoding="utf-8")
        self.registry.register_file(path, entity="candidate", metadata={"promoted": promoted})
        if promoted:
            self.compile()
        return candidate

    def self_retro(self, review: dict[str, Any]) -> dict[str, Any]:
        """Traverse final-review trace signals, infer a root cause, then reinforce.

        This is the AgentRL-side self-retro entrypoint used after a user gives
        final campaign review. Runtime systems still own trace execution; AgentRL
        owns root-cause attribution and harness reinforcement.
        """

        root_cause = self._root_cause_from_trace_review(review)
        instruction = (
            f"Root cause from final review: {root_cause['summary']} "
            f"Improve outcome by adding evidence checks and evaluation coverage for: {review.get('final_review', '')}"
        ).strip()
        result = self.reinforce(
            {
                "source": "agent_driven_final_review_retro",
                "target": root_cause["target"],
                "instruction": instruction,
                "reinforcement_targets": review.get("reinforcement_targets", ["evaluation", "memory", "prompts"]),
                "root_cause": root_cause,
            }
        )
        result["root_cause"] = root_cause
        return result

    def _root_cause_from_trace_review(self, review: dict[str, Any]) -> dict[str, Any]:
        text = " ".join([str(review.get("final_review", "")), *[str(signal) for signal in review.get("signals", [])]]).lower()
        target = str(review.get("target", ""))
        if not target:
            for harness in self.harnesses.values():
                agent_name = str(harness.metadata.get("agent_name", harness.name))
                tokens = {agent_name.lower(), agent_name.lower().replace(" ", "-"), harness.name.lower()}
                if any(token and token in text for token in tokens):
                    target = agent_name
                    break
        target = target or "project"
        summary = "trace evidence gap"
        if "competitor" in text and "pricing" in text:
            summary = "competitor pricing evidence gap"
        elif "citation" in text or "evidence" in text:
            summary = "evidence citation gap"
        elif "metric" in text or "analytics" in text:
            summary = "measurement quality gap"
        return {
            "target": target,
            "summary": summary,
            "trace_paths": list(review.get("trace_paths", [])),
            "signals": list(review.get("signals", [])),
            "final_review": review.get("final_review", ""),
        }

    def reinforce(self, feedback: dict[str, Any]) -> dict[str, Any]:
        """Apply retrospective feedback to the relevant harness lifecycle layer.

        Campaigns can route a retrospective here when the learning points at an
        agent/harness rather than campaign strategy. AgentRL records the feedback,
        updates lightweight lifecycle surfaces, evaluates, versions the candidate,
        and keeps runtime/campaign orchestration outside this repo.
        """

        target = str(feedback.get("target") or feedback.get("agent") or "project")
        instruction = str(feedback.get("instruction") or feedback.get("reinforce") or feedback.get("summary") or "")
        targets = tuple(feedback.get("reinforcement_targets") or ("prompts", "memory", "skills"))
        harness = self._harness_for_reinforcement_target(target)
        reinforcement = {
            "created_at": utc_now(),
            "source": feedback.get("source", "retrospective"),
            "target": target,
            "harness": harness.name if harness else None,
            "instruction": instruction,
            "reinforcement_targets": list(targets),
            "root_cause": feedback.get("root_cause"),
            "raw_feedback": feedback,
        }
        reinforcement_dir = ensure_dir(self.root / ".agentrl" / "reinforcements")
        feedback_path = reinforcement_dir / f"retro-{stable_hash(reinforcement)[:8]}.json"
        feedback_path.write_text(json.dumps(reinforcement, indent=2), encoding="utf-8")

        candidate = {"created_at": utc_now(), "strategy": "retrospective", "targets": list(targets), "changes": []}
        if harness is not None:
            if "prompts" in targets:
                old = harness.prompts.get("system", harness.goal)
                harness.prompts["system"] = old + f"\nRetrospective reinforcement: {instruction}"
                candidate["changes"].append({"harness": harness.name, "target": "prompts", "status": "candidate"})
            if "memory" in targets:
                harness.memory_policy.setdefault("retrospectives", [])
                harness.memory_policy["retrospectives"].append(instruction)
                candidate["changes"].append({"harness": harness.name, "target": "memory", "status": "candidate"})
            if "skills" in targets:
                harness.skills[f"retro_{stable_hash(instruction)[:8]}"] = instruction
                candidate["changes"].append({"harness": harness.name, "target": "skills", "status": "candidate"})
            if "evaluation" in targets:
                harness.rewards.append(RewardSpec(name=f"retro_{stable_hash(instruction)[:8]}", kind="retrospective", weights={"success": 1.0}))
                candidate["changes"].append({"harness": harness.name, "target": "evaluation", "status": "candidate"})
        else:
            candidate["changes"].append({"harness": None, "target": "project", "status": "recorded_only"})

        results = self.evaluate()
        candidate["evaluation"] = [result.to_dict() for result in results]
        candidate["promoted"] = not any(result.failures for result in results)
        archive_dir = ensure_dir(self.root / ".agentrl" / ("candidates" if candidate["promoted"] else "rejected"))
        candidate_path = archive_dir / f"retro-candidate-{stable_hash(candidate)[:8]}.json"
        candidate_path.write_text(json.dumps(candidate, indent=2), encoding="utf-8")
        self.registry.register_file(feedback_path, entity=f"reinforcement:{target}", metadata={"source": reinforcement["source"]})
        self.registry.register_file(candidate_path, entity=f"retro_candidate:{target}", metadata={"promoted": candidate["promoted"]})
        if candidate["promoted"]:
            self.compile()
        return {"status": "reinforced", "target": target, "feedback": reinforcement, "candidate": candidate, "path": str(feedback_path)}

    def _harness_for_reinforcement_target(self, target: str) -> Harness | None:
        normalized = target.lower().replace("_", "-").replace(" ", "-")
        for harness in self.harnesses.values():
            names = {
                harness.name.lower(),
                str(harness.metadata.get("agent_name", "")).lower(),
                str(harness.metadata.get("agent_name", "")).lower().replace(" ", "-"),
            }
            if target.lower() in names or normalized in names:
                return harness
        return None

    def auto_harness(self, mode: str = "static") -> dict[str, Any]:
        if mode not in {"static", "adaptive"}:
            raise ValueError("mode must be static or adaptive")
        return self.evolve(targets=["prompts", "skills", "memory"], strategy="optimization") | {"mode": mode}

    def run_goal(self, goal: str) -> dict[str, Any]:
        plan = ["inspect goal", "select harness", "execute task", "evaluate result"]
        harness = self.harnesses.get("coding") or next(iter(self.harnesses.values()))
        taskset = TaskSet(name="goal_workflow", tasks=[Task(id=f"goal-{stable_hash(goal)[:8]}", description=goal, kind=harness.kind)])
        harness.add_tasks(taskset)
        result = harness.evaluate(self.root, ensure_dir(self.root / ".agentrl" / "traces"))
        return {"goal": goal, "plan": plan, "harness": harness.name, "evaluation": result.to_dict()}

    def deploy(self, strategy: str = "local") -> dict[str, Any]:
        if strategy != "local":
            raise ValueError("MVP supports local deployment; docker/canary/blue_green are future deployment adapters")
        preflight = self.evaluate()
        if any(r.failures for r in preflight):
            return {"strategy": strategy, "created_at": utc_now(), "status": "blocked", "reason": "evaluation_failed", "evaluation": [r.to_dict() for r in preflight]}
        deploy_dir = ensure_dir(self.root / ".agentrl" / "deployments" / "local")
        compiled = self.compile()
        deployment = {"strategy": strategy, "created_at": utc_now(), "harness_versions": compiled, "status": "deployed"}
        path = deploy_dir / "deployment.json"
        path.write_text(json.dumps(deployment, indent=2), encoding="utf-8")
        self.registry.register_file(path, entity="deployment", metadata={"strategy": strategy})
        return deployment

    def promote(self, candidate: dict[str, Any], require_approval: bool = False) -> dict[str, Any]:
        if require_approval and not candidate.get("approved"):
            return {"status": "blocked", "reason": "approval_required", "candidate": candidate}
        self.compile()
        return {"status": "promoted", "candidate": candidate}
