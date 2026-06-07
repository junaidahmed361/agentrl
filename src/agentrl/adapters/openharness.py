from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import hashlib
import json
import urllib.error
import urllib.request

from agentrl.models import Task, TaskSet


@dataclass
class OpenHarnessAdapter:
    """Adapter boundary for OpenHarness-style agent runtimes.

    OpenHarness owns goal -> execution. AgentRL owns execution -> evaluation,
    evolution, versioning, and deployment. This adapter imports runtime outputs
    as lifecycle artifacts without reimplementing tools, MCP, permissions,
    memory, skills, subagents, or an agent loop.
    """

    endpoint: str | None = None
    trace_path: str | None = None
    name: str = "openharness"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_endpoint(cls, endpoint: str, **metadata: Any) -> "OpenHarnessAdapter":
        return cls(endpoint=endpoint.rstrip("/"), metadata=metadata)

    @classmethod
    def from_trace_file(cls, trace_path: str | Path, **metadata: Any) -> "OpenHarnessAdapter":
        return cls(trace_path=str(trace_path), metadata=metadata)

    def to_runtime_record(self) -> dict[str, Any]:
        return {
            "adapter": "OpenHarnessAdapter",
            "name": self.name,
            "endpoint": self.endpoint,
            "trace_path": self.trace_path,
            "boundary": "OpenHarness executes goals; AgentRL evaluates, evolves, versions, and deploys resulting harness behavior.",
            "imports": ["traces", "memory", "skills", "evaluations"],
            "does_not_implement": ["agent_loop", "tools", "mcp", "permissions", "subagents", "context_management"],
            "metadata": self.metadata,
        }

    def to_taskset(self) -> TaskSet:
        traces = self.load_traces()
        tasks = [self._trace_to_task(i, trace) for i, trace in enumerate(traces)]
        return TaskSet(
            name=f"openharness:{self.name}:traces",
            tasks=tasks,
            provenance={
                "adapter": "OpenHarnessAdapter",
                "content_hash": self._content_hash(traces),
                "boundary": "OpenHarness provides runtime trajectories; AgentRL imports them for lifecycle evaluation and versioning.",
                "errors": self.metadata.get("errors", []),
            },
        )

    def load_traces(self) -> list[dict[str, Any]]:
        if self.trace_path:
            try:
                return self._read_records(Path(self.trace_path))
            except (OSError, json.JSONDecodeError, TypeError) as exc:
                self._record_error("openharness_trace_unreadable", {"error": str(exc)})
                return []
        if self.endpoint:
            return self._fetch_endpoint_collection("traces")
        self._record_error("openharness_source_missing")
        return []

    def load_memory(self) -> list[dict[str, Any]]:
        if self.endpoint:
            return self._fetch_endpoint_collection("memory")
        return []

    def load_skills(self) -> list[dict[str, Any]]:
        if self.endpoint:
            return self._fetch_endpoint_collection("skills")
        return []

    def load_evaluations(self) -> list[dict[str, Any]]:
        if self.endpoint:
            return self._fetch_endpoint_collection("evaluations")
        return []

    def _fetch_endpoint_collection(self, collection: str) -> list[dict[str, Any]]:
        if not self.endpoint:
            return []
        url = f"{self.endpoint}/{collection}"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            self._record_error("openharness_endpoint_unavailable", {"collection": collection, "error": str(exc)})
            return []
        return self._normalize_records(payload, collection=collection)

    def _read_records(self, path: Path) -> list[dict[str, Any]]:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".jsonl":
            return self._normalize_records([json.loads(line) for line in text.splitlines() if line.strip()], collection="traces")
        return self._normalize_records(json.loads(text), collection="traces")

    def _normalize_records(self, payload: Any, collection: str) -> list[dict[str, Any]]:
        records = payload.get(collection, payload.get("items", [payload])) if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            self._record_error("openharness_invalid_payload", {"collection": collection, "payload_type": type(records).__name__})
            return []
        normalized = [record for record in records if isinstance(record, dict)]
        if len(normalized) != len(records):
            self._record_error("openharness_invalid_record", {"collection": collection})
            return []
        return normalized

    def _trace_to_task(self, index: int, trace: dict[str, Any]) -> Task:
        goal = trace.get("goal") or trace.get("input") or trace.get("prompt") or "OpenHarness imported execution trace"
        trace_id = trace.get("id") or trace.get("trace_id") or f"openharness-{index}"
        success = trace.get("success")
        if success is None and isinstance(trace.get("evaluation"), dict):
            success = trace["evaluation"].get("success")
        return Task(
            id=str(trace_id),
            description=str(goal),
            kind=str(trace.get("harness") or trace.get("kind") or "runtime"),
            input={"goal": goal, "runtime": "openharness"},
            expected={"success": bool(success) if success is not None else True},
            metadata={
                "openharness": trace,
                "runtime": self.to_runtime_record(),
                "provenance_hash": self._content_hash(trace),
            },
            reward="runtime_success",
        )

    def _record_error(self, reason: str, extra: dict[str, Any] | None = None) -> None:
        data = {"reason": reason, "local_first": True}
        if extra:
            data.update(extra)
        self.metadata.setdefault("errors", []).append(data)

    def _content_hash(self, payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
