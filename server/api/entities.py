from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from server.api.deps import get_entity_store
from server.models import EntityCreate, EntityRecord, EntityType
from server.storage.entity_store import EntityStore


router = APIRouter()


@router.get("/{entity_type}", response_model=list[EntityRecord])
def list_entities(entity_type: EntityType, store: EntityStore = Depends(get_entity_store)) -> list[EntityRecord]:
    return store.list(entity_type)


@router.post("/{entity_type}", response_model=EntityRecord, status_code=201)
def create_entity(
    entity_type: EntityType,
    payload: EntityCreate,
    store: EntityStore = Depends(get_entity_store),
) -> EntityRecord:
    return store.create(entity_type, payload)


@router.get("/{entity_type}/{entity_id}", response_model=EntityRecord)
def get_entity(entity_type: EntityType, entity_id: str, store: EntityStore = Depends(get_entity_store)) -> EntityRecord:
    entity = store.get(entity_type, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.put("/{entity_type}/{entity_id}", response_model=EntityRecord)
def update_entity(
    entity_type: EntityType,
    entity_id: str,
    payload: dict[str, Any],
    store: EntityStore = Depends(get_entity_store),
) -> EntityRecord:
    entity = store.update(entity_type, entity_id, payload)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.delete("/{entity_type}/{entity_id}", status_code=204)
def delete_entity(entity_type: EntityType, entity_id: str, store: EntityStore = Depends(get_entity_store)) -> None:
    deleted = store.delete(entity_type, entity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entity not found")
