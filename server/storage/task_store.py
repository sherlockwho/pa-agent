from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from server.models import TaskCreate, TaskRecord, TaskUpdate
from server.storage.file_store import FileStore


STATUS_HEADINGS = {
    "todo": "待办",
    "doing": "进行中",
    "done": "已完成",
}


class TaskStore:
    def __init__(self, file_store: FileStore):
        self.file_store = file_store

    def list(self, project: str | None = None, status: str | None = None) -> list[TaskRecord]:
        records: list[TaskRecord] = []
        files = [self._path(project)] if project else sorted((self.file_store.data_dir / "tasks").glob("*.md"))
        for path in files:
            records.extend(self._read_file(path))
        if status:
            records = [record for record in records if record.status == status]
        return records

    def create(self, payload: TaskCreate) -> TaskRecord:
        record = TaskRecord(
            **payload.model_dump(),
            id=f"task-{uuid4().hex[:12]}",
            created_at=datetime.now().astimezone(),
        )
        records = self._read_file(self._path(payload.project))
        records.append(record)
        self._write_file(payload.project, records)
        return record

    def update(self, task_id: str, payload: TaskUpdate) -> TaskRecord | None:
        for path in sorted((self.file_store.data_dir / "tasks").glob("*.md")):
            project = path.stem
            records = self._read_file(path)
            for index, record in enumerate(records):
                if record.id != task_id:
                    continue
                data = record.model_dump()
                for key, value in payload.model_dump(exclude_unset=True).items():
                    data[key] = value
                if payload.status == "done" and record.completed_at is None:
                    data["completed_at"] = datetime.now().astimezone()
                if payload.status and payload.status != "done":
                    data["completed_at"] = None
                updated = TaskRecord.model_validate(data)
                records[index] = updated
                self._write_file(project, records)
                return updated
        return None

    def _path(self, project: str | None = "work") -> Path:
        return self.file_store.data_dir / "tasks" / f"{project or 'work'}.md"

    def _read_file(self, path: Path) -> list[TaskRecord]:
        if not path.exists():
            return []
        records: list[TaskRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("<!-- task:"):
                continue
            payload = line.removeprefix("<!-- task:").removesuffix(" -->")
            records.append(TaskRecord.model_validate(json.loads(payload)))
        return records

    def _write_file(self, project: str, records: list[TaskRecord]) -> None:
        path = self._path(project)
        lines = [f"# {project} 任务", ""]
        for status, heading in STATUS_HEADINGS.items():
            lines.extend([f"## {heading}", ""])
            for record in records:
                if record.status != status:
                    continue
                checkbox = "x" if status == "done" else " "
                suffix = []
                suffix.extend(f"#{tag}" for tag in record.tags)
                suffix.extend(f"@{ref}" for ref in record.entity_refs)
                title = f"- [{checkbox}] {record.title}"
                if suffix:
                    title += " " + " ".join(suffix)
                lines.append(title)
                if record.due_date:
                    lines.append(f"  - 截止日期: {record.due_date}")
                if record.notes:
                    lines.append(f"  - 备注: {record.notes}")
                lines.append(
                    "<!-- task:"
                    + json.dumps(record.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
                    + " -->"
                )
            lines.append("")
        self.file_store.write_text(path, "\n".join(lines).rstrip() + "\n")
