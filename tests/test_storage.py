from __future__ import annotations

from datetime import datetime, timedelta

from server.agent.entity_modeler import EntityModeler
from server.config import RAGSettings
from server.models import CalendarEventCreate, CalendarEventUpdate, EntityCreate, TaskCreate, TaskUpdate
from server.rag.indexer import DocumentIndexer
from server.rag.retriever import DocumentRetriever
from server.storage.calendar_store import CalendarStore
from server.storage.conversation_store import ConversationStore
from server.storage.entity_store import EntityStore
from server.storage.file_store import FileStore
from server.storage.memory_store import MemoryStore
from server.storage.task_store import TaskStore


def test_entity_store_creates_and_reads_json(tmp_path):
    store = EntityStore(FileStore(tmp_path))

    created = store.create("product", EntityCreate(name="3535 UVC LED", tags=["UVC"]))
    loaded = store.get("product", created.id)

    assert loaded is not None
    assert loaded.name == "3535 UVC LED"
    assert loaded.tags == ["UVC"]


def test_task_store_writes_markdown_and_updates_status(tmp_path):
    store = TaskStore(FileStore(tmp_path))

    task = store.create(TaskCreate(title="完成工艺规格书修订", tags=["urgent"]))
    updated = store.update(task.id, TaskUpdate(status="done"))

    assert updated is not None
    assert updated.status == "done"
    assert updated.completed_at is not None
    markdown = (tmp_path / "tasks" / "work.md").read_text(encoding="utf-8")
    assert "- [x] 完成工艺规格书修订 #urgent" in markdown


def test_calendar_store_round_trips_ics(tmp_path):
    store = CalendarStore(FileStore(tmp_path))
    start = datetime.now().astimezone().replace(microsecond=0)

    created = store.create(
        CalendarEventCreate(
            title="质量评审会议",
            start_time=start,
            end_time=start + timedelta(hours=1),
            description="准备 8D 报告",
        )
    )
    events = store.list()

    assert len(events) == 1
    assert events[0].id == created.id
    assert events[0].title == "质量评审会议"


def test_calendar_store_updates_and_deletes_event(tmp_path):
    store = CalendarStore(FileStore(tmp_path))
    start = datetime.now().astimezone().replace(microsecond=0)
    event = store.create(CalendarEventCreate(title="旧标题", start_time=start))

    updated = store.update(event.id, CalendarEventUpdate(title="新标题"))
    deleted = store.delete(event.id)

    assert updated is not None
    assert updated.title == "新标题"
    assert deleted is True
    assert store.list() == []


def test_entity_modeler_preserves_project_type(tmp_path):
    entity_store = EntityStore(FileStore(tmp_path))
    modeler = EntityModeler(entity_store)

    records = modeler.upsert_extracted_entities("今天继续推进3535 UVC量产项目")

    assert len(records) == 1
    assert records[0].type == "project"


def test_document_indexer_and_retriever_find_local_content(tmp_path):
    file_store = FileStore(tmp_path)
    document = tmp_path / "documents" / "doc-001__uvc.md"
    document.write_text("3535 UVC LED 工艺规格书\n共晶焊接参数需要控制空洞率。", encoding="utf-8")
    indexer = DocumentIndexer(file_store, RAGSettings(chunk_size=128, chunk_overlap=16, top_k=3))
    retriever = DocumentRetriever(indexer, RAGSettings(top_k=3))

    chunks = indexer.index_document("doc-001", document)
    results = retriever.search("UVC 共晶焊接")

    assert len(chunks) == 1
    assert results
    assert results[0].chunk.document_id == "doc-001"


def test_memory_store_builds_daily_and_global_summary(tmp_path):
    file_store = FileStore(tmp_path)
    conversations = ConversationStore(file_store)
    memory = MemoryStore(file_store, conversations)
    conversations.append("user", "张工说3535 UVC LED项目要更新SOP", entities_extracted=["person-zhang-gong-001"])
    conversations.append("assistant", "已记录", tools_called=["create_task"])

    summary = memory.update_daily_summary()
    context = memory.build_context()
    global_summary = memory.global_summary_path().read_text(encoding="utf-8")

    assert summary.message_count == 2
    assert "create_task" in summary.tools_called
    assert "person-zhang-gong-001" in summary.entities_mentioned
    assert "张工说3535 UVC LED项目要更新SOP" in context
    assert "top_tools" in global_summary
