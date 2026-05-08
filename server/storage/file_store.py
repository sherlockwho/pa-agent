from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from filelock import FileLock


class FileStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.ensure_layout()

    def ensure_layout(self) -> None:
        for relative in [
            "entities/person",
            "entities/company",
            "entities/project",
            "entities/product",
            "calendar",
            "tasks",
            "conversations",
            "documents",
            "memory",
            "index",
        ]:
            (self.data_dir / relative).mkdir(parents=True, exist_ok=True)

    def read_json(self, path: Path, default: Any = None) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(path) + ".lock")
        with lock:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    def append_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(path) + ".lock")
        with lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(text)

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(path) + ".lock")
        with lock:
            path.write_text(text, encoding="utf-8")

    def write_bytes(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(path) + ".lock")
        with lock:
            path.write_bytes(data)
