from __future__ import annotations

from fastapi import Request

from server.storage.calendar_store import CalendarStore
from server.storage.conversation_store import ConversationStore
from server.storage.document_store import DocumentStore
from server.storage.entity_store import EntityStore
from server.storage.memory_store import MemoryStore
from server.storage.task_store import TaskStore


def get_entity_store(request: Request) -> EntityStore:
    return request.app.state.entity_store


def get_task_store(request: Request) -> TaskStore:
    return request.app.state.task_store


def get_calendar_store(request: Request) -> CalendarStore:
    return request.app.state.calendar_store


def get_conversation_store(request: Request) -> ConversationStore:
    return request.app.state.conversation_store


def get_document_store(request: Request) -> DocumentStore:
    return request.app.state.document_store


def get_document_indexer(request: Request):
    return request.app.state.document_indexer


def get_document_retriever(request: Request):
    return request.app.state.document_retriever


def get_memory_store(request: Request) -> MemoryStore:
    return request.app.state.memory_store
