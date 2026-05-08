from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from server.models import DocumentRecord
from server.storage.file_store import FileStore


class DocumentStore:
    def __init__(self, file_store: FileStore):
        self.file_store = file_store

    def list(self) -> list[DocumentRecord]:
        records: list[DocumentRecord] = []
        for path in sorted((self.file_store.data_dir / "documents").glob("*")):
            if path.is_file() and not path.name.endswith(".lock"):
                records.append(self._record_from_path(path))
        return records

    def get_path(self, document_id: str) -> Path | None:
        for path in (self.file_store.data_dir / "documents").glob(f"{document_id}__*"):
            if path.is_file():
                return path
        return None

    def save_upload(self, upload: UploadFile) -> DocumentRecord:
        document_id = f"doc-{uuid4().hex[:12]}"
        safe_name = Path(upload.filename or "document").name
        path = self.file_store.data_dir / "documents" / f"{document_id}__{safe_name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        return self._record_from_path(path, content_type=upload.content_type)

    def _record_from_path(self, path: Path, content_type: str | None = None) -> DocumentRecord:
        document_id = path.name.split("__", 1)[0]
        filename = path.name.split("__", 1)[1] if "__" in path.name else path.name
        stat = path.stat()
        return DocumentRecord(
            id=document_id,
            filename=filename,
            path=str(path),
            content_type=content_type,
            size_bytes=stat.st_size,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime).astimezone(),
        )
