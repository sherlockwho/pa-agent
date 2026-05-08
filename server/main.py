from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.agent.llm import DeepSeekClient
from server.agent.entity_modeler import EntityModeler
from server.agent.memory import ShortTermMemory
from server.agent.orchestrator import Orchestrator
from server.api import calendar, chat, entities, files, memory, tasks
from server.api.auth import TokenAuthMiddleware
from server.config import get_settings
from server.rag.indexer import DocumentIndexer
from server.rag.retriever import DocumentRetriever
from server.skills.calendar_skill import CalendarSkill
from server.skills.doc_skill import DocSkill
from server.skills.email_skill import EmailSkill
from server.skills.entity_skill import EntitySkill
from server.skills.task_skill import TaskSkill
from server.storage.calendar_store import CalendarStore
from server.storage.conversation_store import ConversationStore
from server.storage.document_store import DocumentStore
from server.storage.entity_store import EntityStore
from server.storage.file_store import FileStore
from server.storage.memory_store import MemoryStore
from server.storage.task_store import TaskStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    file_store = FileStore(settings.data_dir)
    conversation_store = ConversationStore(file_store)
    entity_store = EntityStore(file_store)
    task_store = TaskStore(file_store)
    calendar_store = CalendarStore(file_store)
    document_store = DocumentStore(file_store)
    document_indexer = DocumentIndexer(file_store, settings.rag, settings.embedding)
    document_retriever = DocumentRetriever(document_indexer, settings.rag)
    memory_store = MemoryStore(file_store, conversation_store)
    entity_modeler = EntityModeler(entity_store)
    memory = ShortTermMemory(max_messages=settings.memory.max_short_term_messages)
    llm = DeepSeekClient(settings.llm)
    skills = [
        TaskSkill(task_store),
        CalendarSkill(calendar_store),
        DocSkill(document_retriever),
        EntitySkill(entity_store),
        EmailSkill(settings.email),
    ]

    app.state.settings = settings
    app.state.llm = llm
    app.state.file_store = file_store
    app.state.conversation_store = conversation_store
    app.state.entity_store = entity_store
    app.state.task_store = task_store
    app.state.calendar_store = calendar_store
    app.state.document_store = document_store
    app.state.document_indexer = document_indexer
    app.state.document_retriever = document_retriever
    app.state.memory_store = memory_store
    app.state.orchestrator = Orchestrator(
        llm=llm,
        memory=memory,
        conversations=conversation_store,
        task_store=task_store,
        calendar_store=calendar_store,
        entity_store=entity_store,
        document_retriever=document_retriever,
        entity_modeler=entity_modeler,
        long_term_memory=memory_store,
        skills=skills,
    )
    yield


app = FastAPI(title="Personal AI Work Assistant", version="0.1.0", lifespan=lifespan)
app.add_middleware(TokenAuthMiddleware)

app.include_router(chat.router)
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(entities.router, prefix="/api/entities", tags=["entities"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
