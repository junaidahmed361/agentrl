from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
import hashlib
import json

JsonDict = dict[str, Any]
RewardFn = Callable[["Task", JsonDict], float]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class Task:
    id: str
    description: str
    kind: str
    input: JsonDict = field(default_factory=dict)
    expected: JsonDict = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)
    reward: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "Task":
        return cls(**data)


@dataclass
class TaskSet:
    name: str
    tasks: list[Task] = field(default_factory=list)
    provenance: JsonDict = field(default_factory=dict)

    def add(self, task: Task) -> None:
        self.tasks.append(task)

    def extend(self, tasks: Iterable[Task]) -> None:
        self.tasks.extend(tasks)

    def to_dict(self) -> JsonDict:
        return {"name": self.name, "tasks": [t.to_dict() for t in self.tasks], "provenance": self.provenance}

    @classmethod
    def from_dict(cls, data: JsonDict) -> "TaskSet":
        return cls(name=data["name"], tasks=[Task.from_dict(t) for t in data.get("tasks", [])], provenance=data.get("provenance", {}))

    def content_hash(self) -> str:
        return stable_hash(self.to_dict())


@dataclass
class RewardSpec:
    name: str
    kind: str = "verification"
    weights: dict[str, float] = field(default_factory=lambda: {"success": 1.0})
    executable: str | None = None
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return asdict(self)

    def score(self, task: Task, result: JsonDict) -> float:
        if "score" in result:
            return float(result["score"])
        success = bool(result.get("success"))
        return self.weights.get("success", 1.0) if success else 0.0


@dataclass
class EvaluationResult:
    harness: str
    task_count: int
    average_reward: float
    pass_rate: float
    rewards: list[float]
    failures: list[JsonDict] = field(default_factory=list)
    trace_path: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class VersionRecord:
    id: str
    entity: str
    path: str
    created_at: str
    content_hash: str
    metadata: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return asdict(self)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
