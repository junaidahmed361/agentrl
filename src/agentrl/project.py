from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import yaml

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
            "Run it with:\n\n"
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

    def compile(self) -> list[dict[str, Any]]:
        compiled_dir = ensure_dir(self.root / ".agentrl" / "compiled")
        records = []
        for harness in self.harnesses.values():
            path = harness.compile(compiled_dir)
            records.append(self.registry.register_file(path, entity=f"harness:{harness.name}", metadata={"kind": harness.kind}).to_dict())
        return records

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
