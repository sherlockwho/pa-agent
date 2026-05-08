from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from server.api.deps import get_memory_store
from server.models import MemorySummary
from server.storage.memory_store import MemoryStore


router = APIRouter()


@router.get("/daily", response_model=list[MemorySummary])
def list_daily_summaries(store: MemoryStore = Depends(get_memory_store)) -> list[MemorySummary]:
    return store.list_daily_summaries()


@router.post("/daily/{day}", response_model=MemorySummary)
async def rebuild_daily_summary(
    day: str,
    request: Request,
    store: MemoryStore = Depends(get_memory_store),
) -> MemorySummary:
    llm = getattr(request.app.state, "llm", None)
    return await store.update_daily_summary_with_llm(day=day, llm=llm)


@router.post("/daily", response_model=MemorySummary)
async def rebuild_today_summary(
    request: Request,
    store: MemoryStore = Depends(get_memory_store),
) -> MemorySummary:
    llm = getattr(request.app.state, "llm", None)
    return await store.update_daily_summary_with_llm(llm=llm)


@router.get("/weekly", response_model=list[dict])
def list_weekly_summaries(store: MemoryStore = Depends(get_memory_store)) -> list[dict]:
    return store.list_weekly_summaries()


@router.post("/weekly", response_model=dict)
async def rebuild_weekly_summary(
    request: Request,
    week_start: str | None = Query(default=None, description="ISO date of Monday, e.g. 2026-05-04"),
    store: MemoryStore = Depends(get_memory_store),
) -> dict:
    llm = getattr(request.app.state, "llm", None)
    return await store.generate_weekly_summary(week_start=week_start, llm=llm)


@router.get("/context")
def get_memory_context(
    days: int = Query(default=3, ge=1, le=30),
    store: MemoryStore = Depends(get_memory_store),
) -> dict[str, str]:
    return {"context": store.build_context(days=days)}
