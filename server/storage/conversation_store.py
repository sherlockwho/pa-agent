from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from server.models import ConversationRecord
from server.storage.file_store import FileStore


class ConversationStore:
    def __init__(self, file_store: FileStore):
        self.file_store = file_store

    def append(
        self,
        role: str,
        content: str,
        session_id: str = "default",
        entities_extracted: list[str] | None = None,
        tools_called: list[str] | None = None,
    ) -> ConversationRecord:
        now = datetime.now().astimezone()
        record = ConversationRecord(
            id=f"msg-{uuid4().hex[:12]}",
            timestamp=now,
            role=role,
            content=content,
            session_id=session_id,
            entities_extracted=entities_extracted or [],
            tools_called=tools_called or [],
        )
        path = self.file_store.data_dir / "conversations" / f"{now.date().isoformat()}.jsonl"
        self.file_store.append_text(
            path,
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n",
        )
        return record

    def list_days(self) -> list[Path]:
        path = self.file_store.data_dir / "conversations"
        return sorted(path.glob("*.jsonl"))
