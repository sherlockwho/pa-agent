from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from server.main import app


def cleanup_runtime_files() -> None:
    for path in Path("data/conversations").glob("*.jsonl"):
        path.unlink()
    for path in Path("data/memory").glob("*.yaml"):
        path.unlink()
    for entity_type in ["person", "company", "project", "product"]:
        for path in Path("data/entities").joinpath(entity_type).glob("*.json"):
            path.unlink()


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_file_upload_indexes_and_searches_document():
    uploaded_path: Path | None = None
    index_path = Path("data/index/docs_chunks.jsonl")
    with TestClient(app) as client:
        upload = client.post(
            "/api/files/",
            files={"upload": ("uvc.md", b"3535 UVC LED process document", "text/markdown")},
        )
        search = client.get("/api/files/search", params={"q": "UVC process"})
        if upload.status_code == 201:
            uploaded_path = Path(upload.json()["path"])

    assert upload.status_code == 201
    assert search.status_code == 200
    assert search.json()[0]["chunk"]["source_file"].endswith("uvc.md")
    if uploaded_path and uploaded_path.exists():
        uploaded_path.unlink()
    if index_path.exists():
        index_path.unlink()
    cleanup_runtime_files()


def test_websocket_can_create_task_with_local_tool():
    created_task_file = Path("data/tasks/work.md")
    if created_task_file.exists():
        created_task_file.unlink()

    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"message": "帮我创建任务：完成UVC工艺规格书修订 截止 2026-05-20"})
            token = websocket.receive_json()
            done = websocket.receive_json()

    assert token["type"] == "token"
    assert "已创建任务" in token["content"]
    assert done == {"type": "done"}
    assert created_task_file.exists()
    assert "完成UVC工艺规格书修订" in created_task_file.read_text(encoding="utf-8")
    created_task_file.unlink()
    cleanup_runtime_files()


def test_websocket_can_create_calendar_event_with_local_tool():
    calendar_file = Path("data/calendar/default.ics")
    if calendar_file.exists():
        calendar_file.unlink()

    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"message": "帮我安排会议：质量评审 2026-05-20 10:30"})
            token = websocket.receive_json()
            done = websocket.receive_json()

    assert token["type"] == "token"
    assert "已创建日程" in token["content"]
    assert done == {"type": "done"}
    assert calendar_file.exists()
    assert "质量评审" in calendar_file.read_text(encoding="utf-8")
    assert "SUMMARY:质量评审" in calendar_file.read_text(encoding="utf-8")
    calendar_file.unlink()
    cleanup_runtime_files()


def test_websocket_can_search_documents_with_local_tool():
    document_path = Path("data/documents/doc-test__uvc.md")
    index_path = Path("data/index/docs_chunks.jsonl")
    document_path.write_text("UVC LED 共晶焊接空洞率控制方法", encoding="utf-8")

    with TestClient(app) as client:
        client.post("/api/files/reindex")
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"message": "帮我检索文档：UVC 共晶焊接"})
            token = websocket.receive_json()
            done = websocket.receive_json()

    assert token["type"] == "token"
    assert "本地知识库检索结果" in token["content"]
    assert "共晶焊接" in token["content"]
    assert done == {"type": "done"}
    document_path.unlink()
    if index_path.exists():
        index_path.unlink()
    cleanup_runtime_files()


def test_websocket_auto_extracts_entities_and_updates_memory():
    cleanup_runtime_files()

    with TestClient(app) as client:
        with client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"message": "张工说3535 UVC LED项目下周要更新SOP"})
            websocket.receive_json()
            websocket.receive_json()
        entities = client.get("/api/entities/product").json()
        memory_context = client.get("/api/memory/context").json()["context"]

    assert any("3535" in entity["name"] for entity in entities)
    assert "长期记忆摘要" in memory_context
    assert "3535 UVC LED项目" in memory_context
    cleanup_runtime_files()
