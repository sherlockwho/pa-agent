from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from server.api.deps import get_calendar_store
from server.models import CalendarEventCreate, CalendarEventRecord, CalendarEventUpdate
from server.storage.calendar_store import CalendarStore


router = APIRouter()


@router.get("/", response_model=list[CalendarEventRecord])
def list_events(
    calendar: str = Query(default="default"),
    store: CalendarStore = Depends(get_calendar_store),
) -> list[CalendarEventRecord]:
    return store.list(calendar=calendar)


@router.post("/", response_model=CalendarEventRecord, status_code=201)
def create_event(
    payload: CalendarEventCreate,
    store: CalendarStore = Depends(get_calendar_store),
) -> CalendarEventRecord:
    return store.create(payload)


@router.patch("/{event_id}", response_model=CalendarEventRecord)
def update_event(
    event_id: str,
    payload: CalendarEventUpdate,
    calendar: str = Query(default="default"),
    store: CalendarStore = Depends(get_calendar_store),
) -> CalendarEventRecord:
    event = store.update(event_id, payload, calendar_name=calendar)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return event


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: str,
    calendar: str = Query(default="default"),
    store: CalendarStore = Depends(get_calendar_store),
) -> None:
    deleted = store.delete(event_id, calendar_name=calendar)
    if not deleted:
        raise HTTPException(status_code=404, detail="Calendar event not found")
