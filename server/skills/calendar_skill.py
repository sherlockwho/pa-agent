from __future__ import annotations

from typing import Any

from server.models import CalendarEventCreate, CalendarEventUpdate
from server.skills.base import BaseSkill
from server.storage.calendar_store import CalendarStore


class CalendarSkill(BaseSkill):
    def __init__(self, store: CalendarStore):
        self.store = store

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return "iCalendar-backed schedule management"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_calendar_event",
                    "description": "创建一个日程事件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["title", "start_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_calendar_events",
                    "description": "查询默认日历中的事件",
                    "parameters": {
                        "type": "object",
                        "properties": {"calendar": {"type": "string", "default": "default"}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_calendar_event",
                    "description": "更新一个日程事件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["id"],
                    },
                },
            }
        ]

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "create_calendar_event":
            event = self.store.create(CalendarEventCreate.model_validate(parameters))
            return event.model_dump(mode="json")
        if tool_name == "query_calendar_events":
            events = self.store.list(calendar=parameters.get("calendar", "default"))
            return {"events": [event.model_dump(mode="json") for event in events]}
        if tool_name == "update_calendar_event":
            event_id = parameters.pop("id")
            calendar = parameters.pop("calendar", "default")
            event = self.store.update(event_id, CalendarEventUpdate.model_validate(parameters), calendar_name=calendar)
            return event.model_dump(mode="json") if event else {"error": "event_not_found"}
        return {"error": "unknown_tool"}
