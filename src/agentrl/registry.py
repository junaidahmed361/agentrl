from __future__ import annotations

from pathlib import Path
from typing import Any
import difflib
import json
import shutil

from .models import VersionRecord, stable_hash, utc_now


class VersionRegistry:
    def __init__(self, root: Path):
        self.root = root
        self.store = root / ".agentrl" / "registry"
        self.index_path = self.store / "index.json"
        self.artifacts = self.store / "artifacts"
        self.store.mkdir(parents=True, exist_ok=True)
        self.artifacts.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            return []
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save(self, records: list[dict[str, Any]]) -> None:
        self.index_path.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")

    def register_file(self, path: Path, entity: str, metadata: dict[str, Any] | None = None) -> VersionRecord:
        content = path.read_bytes()
        source_path = str(path.relative_to(self.root))
        content_hash = stable_hash({"path": source_path, "content": content.decode("utf-8", errors="replace")})
        version_id = f"{entity}-{len(self._load()) + 1:04d}-{content_hash[:8]}"
        dest = self.artifacts / version_id / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        record_metadata = {"source_path": source_path} | (metadata or {})
        record = VersionRecord(version_id, entity, str(dest.relative_to(self.root)), utc_now(), content_hash, record_metadata)
        records = self._load()
        records.append(record.to_dict())
        self._save(records)
        return record

    def list(self, entity: str | None = None) -> list[dict[str, Any]]:
        records = self._load()
        if entity:
            records = [r for r in records if r["entity"] == entity]
        return records

    def diff(self, left_id: str, right_id: str) -> str:
        records = {r["id"]: r for r in self._load()}
        missing = [version_id for version_id in (left_id, right_id) if version_id not in records]
        if missing:
            raise ValueError(f"unknown version id(s): {', '.join(missing)}")
        left = self.root / records[left_id]["path"]
        right = self.root / records[right_id]["path"]
        return "".join(difflib.unified_diff(
            left.read_text(encoding="utf-8").splitlines(True),
            right.read_text(encoding="utf-8").splitlines(True),
            fromfile=left_id,
            tofile=right_id,
        ))

    def rollback(self, version_id: str, target: Path | None = None) -> Path:
        records = {r["id"]: r for r in self._load()}
        if version_id not in records:
            raise ValueError(f"unknown version id: {version_id}")
        record = records[version_id]
        src = self.root / record["path"]
        source_path = record.get("metadata", {}).get("source_path")
        dest = target or (self.root / source_path if source_path else self.root / "compiled" / src.name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return dest
