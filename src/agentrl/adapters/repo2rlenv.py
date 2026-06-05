from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import hashlib
import json
import subprocess

from agentrl.models import Task, TaskSet


@dataclass
class Repo2RLEnvAdapter:
    repo: str
    pipeline: str = "pr_runtime"
    limit: int | None = None
    output_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_repo(cls, repo: str, pipeline: str = "pr_runtime", limit: int | None = None, output_path: str | None = None, **metadata: Any) -> "Repo2RLEnvAdapter":
        return cls(repo=repo, pipeline=pipeline, limit=limit, output_path=output_path, metadata=metadata)

    def to_taskset(self) -> TaskSet:
        raw_tasks = self._load_or_generate()
        tasks = [self._map_task(i, raw) for i, raw in enumerate(raw_tasks[: self.limit or len(raw_tasks)])]
        return TaskSet(
            name=f"repo2rlenv:{self.repo}:{self.pipeline}",
            tasks=tasks,
            provenance={
                "adapter": "Repo2RLEnvAdapter",
                "repo": self.repo,
                "pipeline": self.pipeline,
                "content_hash": self._content_hash(raw_tasks),
                "boundary": "Repo2RLEnv creates verifiable coding tasks; AgentRL imports them into CodingHarness.",
                "errors": self.metadata.get("errors", []),
            },
        )

    def _load_or_generate(self) -> list[dict[str, Any]]:
        if self.output_path:
            try:
                return self._read_tasks(Path(self.output_path))
            except (OSError, json.JSONDecodeError, TypeError) as exc:
                self._record_error("repo2rlenv_output_unreadable", {"error": str(exc)})
                return []
        cmd = ["repo2rlenv", "generate", "--repo", self.repo, "--pipeline", self.pipeline, "--format", "json"]
        try:
            proc = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
        except FileNotFoundError:
            self._record_error("repo2rlenv_cli_missing")
            return []
        if proc.returncode != 0:
            self._record_error("repo2rlenv_generation_failed", {"stderr": proc.stderr[-2000:]})
            return []
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self._record_error("repo2rlenv_invalid_json", {"stdout": proc.stdout[-2000:]})
            return []
        return self._normalize_payload(payload)

    def _read_tasks(self, path: Path) -> list[dict[str, Any]]:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".jsonl":
            return self._normalize_payload([json.loads(line) for line in text.splitlines() if line.strip()])
        return self._normalize_payload(json.loads(text))

    def _normalize_payload(self, payload: Any) -> list[dict[str, Any]]:
        tasks = payload.get("tasks", [payload]) if isinstance(payload, dict) else payload
        if not isinstance(tasks, list):
            self._record_error("repo2rlenv_invalid_tasks", {"payload_type": type(tasks).__name__})
            return []
        normalized = [task for task in tasks if isinstance(task, dict)]
        if len(normalized) != len(tasks):
            self._record_error("repo2rlenv_invalid_task", {"payload_type": type(payload).__name__})
            return []
        return normalized

    def _map_task(self, index: int, raw: dict[str, Any]) -> Task:
        task_id = raw.get("id") or raw.get("task_id") or f"{self.repo.replace('/', '-')}-{index}"
        description = raw.get("description") or raw.get("prompt") or raw.get("issue") or "Repo2RLEnv imported coding task"
        command = raw.get("verification_command") or raw.get("test_command") or raw.get("reward", {}).get("command") or "pytest -q"
        sandbox = raw.get("sandbox") or raw.get("environment") or {}
        metadata = {
            "repo2rlenv": raw,
            "repo": self.repo,
            "pipeline": self.pipeline,
            "sandbox": sandbox,
            "harbor": raw.get("harbor") or raw.get("metadata", {}).get("harbor"),
            "provenance_hash": self._content_hash(raw),
        }
        return Task(
            id=str(task_id),
            description=str(description),
            kind="coding",
            input={"repo": self.repo, "patch": raw.get("patch"), "files": raw.get("files", [])},
            expected={"command": command, "timeout": raw.get("timeout", 120)},
            metadata=metadata,
            reward="pytest",
        )

    def _record_error(self, reason: str, extra: dict[str, Any] | None = None) -> None:
        data = {"reason": reason, "local_first": True}
        if extra:
            data.update(extra)
        self.metadata.setdefault("errors", []).append(data)

    def _content_hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
