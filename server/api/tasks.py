from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from server.api.deps import get_task_store
from server.models import TaskCreate, TaskRecord, TaskUpdate
from server.storage.task_store import TaskStore


router = APIRouter()


@router.get("/", response_model=list[TaskRecord])
def list_tasks(
    project: str | None = Query(default=None),
    status: str | None = Query(default=None),
    store: TaskStore = Depends(get_task_store),
) -> list[TaskRecord]:
    return store.list(project=project, status=status)


@router.post("/", response_model=TaskRecord, status_code=201)
def create_task(payload: TaskCreate, store: TaskStore = Depends(get_task_store)) -> TaskRecord:
    return store.create(payload)


@router.patch("/{task_id}", response_model=TaskRecord)
def update_task(task_id: str, payload: TaskUpdate, store: TaskStore = Depends(get_task_store)) -> TaskRecord:
    task = store.update(task_id, payload)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, store: TaskStore = Depends(get_task_store)) -> None:
    deleted = store.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/", status_code=204)
def delete_all_tasks(
    status: str | None = Query(default=None),
    store: TaskStore = Depends(get_task_store),
) -> None:
    store.delete_all(status=status)
