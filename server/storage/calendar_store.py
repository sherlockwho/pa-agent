from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from icalendar import Calendar, Event

from server.models import CalendarEventCreate, CalendarEventRecord, CalendarEventUpdate
from server.storage.file_store import FileStore


class CalendarStore:
    def __init__(self, file_store: FileStore):
        self.file_store = file_store

    def list(self, calendar: str = "default") -> list[CalendarEventRecord]:
        path = self._path(calendar)
        if not path.exists():
            return []
        parsed = Calendar.from_ical(path.read_bytes())
        records: list[CalendarEventRecord] = []
        for component in parsed.walk("VEVENT"):
            records.append(self._event_to_record(component, calendar))
        return sorted(records, key=lambda event: event.start_time)

    def create(self, payload: CalendarEventCreate) -> CalendarEventRecord:
        record = CalendarEventRecord(
            **payload.model_dump(),
            id=f"evt-{uuid4().hex[:12]}",
            created_at=datetime.now().astimezone(),
        )
        path = self._path(payload.calendar)
        calendar = self._load_calendar(path)
        event = Event()
        event.add("uid", record.id)
        event.add("summary", record.title)
        event.add("dtstart", record.start_time)
        event.add("dtend", record.end_time or record.start_time)
        event.add("description", record.description)
        event.add("created", record.created_at)
        if record.reminder_minutes is not None:
            event.add("x-reminder-minutes", record.reminder_minutes)
        calendar.add_component(event)
        self.file_store.write_bytes(path, calendar.to_ical())
        return record

    def update(self, event_id: str, payload: CalendarEventUpdate, calendar_name: str = "default") -> CalendarEventRecord | None:
        path = self._path(calendar_name)
        if not path.exists():
            return None
        calendar = self._load_calendar(path)
        for event in calendar.walk("VEVENT"):
            if str(event.get("uid")) != event_id:
                continue
            current = self._event_to_record(event, calendar_name)
            data = current.model_dump()
            for key, value in payload.model_dump(exclude_unset=True).items():
                data[key] = value
            updated = CalendarEventRecord.model_validate(data)
            self._replace_event_fields(event, updated)
            self.file_store.write_bytes(path, calendar.to_ical())
            return updated
        return None

    def delete_all(self, calendar_name: str = "default") -> int:
        path = self._path(calendar_name)
        if not path.exists():
            return 0
        calendar = self._load_calendar(path)
        count = sum(1 for c in calendar.subcomponents if c.name == "VEVENT")
        empty = Calendar()
        empty.add("prodid", "-//Personal AI Work Assistant//local//")
        empty.add("version", "2.0")
        self.file_store.write_bytes(path, empty.to_ical())
        return count

    def delete(self, event_id: str, calendar_name: str = "default") -> bool:
        path = self._path(calendar_name)
        if not path.exists():
            return False
        calendar = self._load_calendar(path)
        kept = Calendar()
        kept.add("prodid", "-//Personal AI Work Assistant//local//")
        kept.add("version", "2.0")
        deleted = False
        for component in calendar.subcomponents:
            if component.name == "VEVENT" and str(component.get("uid")) == event_id:
                deleted = True
                continue
            kept.add_component(component)
        if deleted:
            self.file_store.write_bytes(path, kept.to_ical())
        return deleted

    def _path(self, calendar: str) -> Path:
        return self.file_store.data_dir / "calendar" / f"{calendar}.ics"

    def _load_calendar(self, path: Path) -> Calendar:
        if path.exists():
            return Calendar.from_ical(path.read_bytes())
        path.parent.mkdir(parents=True, exist_ok=True)
        calendar = Calendar()
        calendar.add("prodid", "-//Personal AI Work Assistant//local//")
        calendar.add("version", "2.0")
        return calendar

    def _event_to_record(self, event: Event, calendar: str) -> CalendarEventRecord:
        start = event.decoded("dtstart")
        end = event.decoded("dtend", start)
        created = event.decoded("created", datetime.now().astimezone())
        reminder = event.get("x-reminder-minutes")
        return CalendarEventRecord(
            id=str(event.get("uid")),
            title=str(event.get("summary", "")),
            start_time=start,
            end_time=end,
            description=str(event.get("description", "")),
            calendar=calendar,
            reminder_minutes=int(reminder) if reminder is not None else None,
            created_at=created,
        )

    def _replace_event_fields(self, event: Event, record: CalendarEventRecord) -> None:
        for key in ["summary", "dtstart", "dtend", "description", "x-reminder-minutes"]:
            if key in event:
                del event[key]
        event.add("summary", record.title)
        event.add("dtstart", record.start_time)
        event.add("dtend", record.end_time or record.start_time)
        event.add("description", record.description)
        if record.reminder_minutes is not None:
            event.add("x-reminder-minutes", record.reminder_minutes)
