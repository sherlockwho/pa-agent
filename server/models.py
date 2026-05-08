from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


EntityType = Literal["person", "company", "project", "product"]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ConversationRecord(BaseModel):
    id: str
    timestamp: datetime
    role: Literal["user", "assistant", "system"]
    content: str
    session_id: str = "default"
    entities_extracted: list[str] = Field(default_factory=list)
    tools_called: list[str] = Field(default_factory=list)


class MemorySummary(BaseModel):
    date: str
    message_count: int = 0
    user_message_count: int = 0
    assistant_message_count: int = 0
    tools_called: list[str] = Field(default_factory=list)
    entities_mentioned: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    narrative: str = ""
    updated_at: datetime


class EntityCreate(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[dict[str, Any]] = Field(default_factory=list)


class EntityRecord(EntityCreate):
    id: str
    type: EntityType
    first_mentioned: str | None = None
    last_updated: str
    mention_count: int = 1


class TaskCreate(BaseModel):
    title: str
    project: str = "work"
    status: Literal["todo", "doing", "done"] = "todo"
    due_date: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    entity_refs: list[str] = Field(default_factory=list)


class TaskRecord(TaskCreate):
    id: str
    created_at: datetime
    completed_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    status: Literal["todo", "doing", "done"] | None = None
    due_date: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    entity_refs: list[str] | None = None


class CalendarEventCreate(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime | None = None
    description: str = ""
    calendar: str = "default"
    reminder_minutes: int | None = None


class CalendarEventRecord(CalendarEventCreate):
    id: str
    created_at: datetime


class CalendarEventUpdate(BaseModel):
    title: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    description: str | None = None
    reminder_minutes: int | None = None


class DocumentRecord(BaseModel):
    id: str
    filename: str
    path: str
    content_type: str | None = None
    size_bytes: int
    uploaded_at: datetime


class RAGChunk(BaseModel):
    id: str
    document_id: str
    source_file: str
    position: int
    text: str


class RAGSearchResult(BaseModel):
    chunk: RAGChunk
    score: float
