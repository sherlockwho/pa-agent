from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from server.models import EntityCreate, EntityRecord, EntityType
from server.storage.file_store import FileStore


VALID_ENTITY_TYPES: set[str] = {"person", "company", "project", "product"}


def slugify_name(name: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z一-鿿]+", "-", name.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "entity"


class EntityStore:
    def __init__(self, file_store: FileStore):
        self.file_store = file_store

    def _dir(self, entity_type: EntityType) -> Path:
        if entity_type not in VALID_ENTITY_TYPES:
            raise ValueError(f"Unsupported entity type: {entity_type}")
        return self.file_store.data_dir / "entities" / entity_type

    def _path(self, entity_type: EntityType, entity_id: str) -> Path:
        return self._dir(entity_type) / f"{entity_id}.json"

    def list(self, entity_type: EntityType) -> list[EntityRecord]:
        records: list[EntityRecord] = []
        for path in sorted(self._dir(entity_type).glob("*.json")):
            if path.name.endswith(".lock"):
                continue
            records.append(EntityRecord.model_validate(self.file_store.read_json(path)))
        return records

    def get(self, entity_type: EntityType, entity_id: str) -> EntityRecord | None:
        path = self._path(entity_type, entity_id)
        payload = self.file_store.read_json(path)
        return EntityRecord.model_validate(payload) if payload else None

    def create(self, entity_type: EntityType, payload: EntityCreate) -> EntityRecord:
        today = date.today().isoformat()
        entity_id = self._next_id(entity_type, payload.name)
        record = EntityRecord(
            id=entity_id,
            type=entity_type,
            name=payload.name,
            aliases=payload.aliases,
            attributes=payload.attributes,
            tags=payload.tags,
            relations=payload.relations,
            notes=payload.notes,
            first_mentioned=today,
            last_updated=today,
        )
        self.file_store.write_json(self._path(entity_type, entity_id), record.model_dump(mode="json"))
        return record

    def update(self, entity_type: EntityType, entity_id: str, payload: dict[str, Any]) -> EntityRecord | None:
        record = self.get(entity_type, entity_id)
        if not record:
            return None
        current = record.model_dump()
        current.update(payload)
        current["last_updated"] = date.today().isoformat()
        updated = EntityRecord.model_validate(current)
        self.file_store.write_json(self._path(entity_type, entity_id), updated.model_dump(mode="json"))
        return updated

    def delete(self, entity_type: EntityType, entity_id: str) -> bool:
        path = self._path(entity_type, entity_id)
        if not path.exists():
            return False
        path.unlink()
        lock_path = Path(str(path) + ".lock")
        if lock_path.exists():
            lock_path.unlink()
        return True

    def find_by_name(self, entity_type: EntityType, name: str) -> EntityRecord | None:
        """Exact and alias match first; vector similarity fallback when FAISS available."""
        needle = name.strip().lower()
        records = self.list(entity_type)

        # 1. Exact / alias match
        for record in records:
            candidates = [record.name, *record.aliases]
            if any(c.lower() == needle for c in candidates):
                return record

        # 2. Vector similarity (when sentence-transformers + faiss are installed)
        best = self._vector_find(entity_type, name, records)
        if best:
            return best

        return None

    def _vector_find(
        self,
        entity_type: EntityType,
        name: str,
        records: list[EntityRecord],
        threshold: float = 0.85,
    ) -> EntityRecord | None:
        if not records:
            return None
        try:
            import faiss
            import numpy as np
            from sentence_transformers import SentenceTransformer

            model = _get_entity_model()
            candidate_names = [r.name for r in records]
            all_names = [name, *candidate_names]
            vecs = model.encode(all_names, normalize_embeddings=True, show_progress_bar=False)
            vecs = np.array(vecs, dtype=np.float32)

            query = vecs[0:1]
            corpus = vecs[1:]

            index = faiss.IndexFlatIP(corpus.shape[1])
            index.add(corpus)
            scores, ids = index.search(query, 1)

            if scores[0][0] >= threshold:
                return records[int(ids[0][0])]
        except Exception:
            pass
        return None

    def _next_id(self, entity_type: EntityType, name: str) -> str:
        slug = slugify_name(name)
        existing = {path.stem for path in self._dir(entity_type).glob(f"{entity_type}-{slug}-*.json")}
        index = 1
        while True:
            candidate = f"{entity_type}-{slug}-{index:03d}"
            if candidate not in existing:
                return candidate
            index += 1


# Module-level model cache (shared across all EntityStore instances)
_entity_model: Any = None


def _get_entity_model() -> Any:
    global _entity_model
    if _entity_model is None:
        from sentence_transformers import SentenceTransformer
        _entity_model = SentenceTransformer("BAAI/bge-small-zh-v1.5", device="cpu")
    return _entity_model
