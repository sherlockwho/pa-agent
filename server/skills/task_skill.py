from __future__ import annotations

from typing import Any

from server.models import TaskCreate, TaskUpdate
from server.skills.base import BaseSkill
from server.storage.task_store import TaskStore


class TaskSkill(BaseSkill):
    def __init__(self, store: TaskStore):
        self.store = store

    @property
    def name(self) -> str:
        return "tasks"

    @property
    def description(self) -> str:
        return "Markdown-backed task tracking"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_task",
                    "description": "创建一个待办任务",
                    "parameters": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}, "due_date": {"type": "string"}},
                        "required": ["title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_tasks",
                    "description": "查询本地任务列表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "status": {"type": "string", "enum": ["todo", "doing", "done"]},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_task",
                    "description": "更新任务状态或信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "status": {"type": "string", "enum": ["todo", "doing", "done"]},
                            "title": {"type": "string"},
                            "due_date": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_task",
                    "description": "删除指定任务（按 ID）",
                    "parameters": {
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                        "required": ["id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_all_tasks",
                    "description": "删除所有任务，可按状态过滤",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["todo", "doing", "done"]},
                        },
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "create_task":
            task = self.store.create(TaskCreate.model_validate(parameters))
            return task.model_dump(mode="json")
        if tool_name == "update_task":
            task_id = parameters.pop("id")
            task = self.store.update(task_id, TaskUpdate.model_validate(parameters))
            return task.model_dump(mode="json") if task else {"error": "task_not_found"}
        if tool_name == "query_tasks":
            tasks = self.store.list(project=parameters.get("project"), status=parameters.get("status"))
            return {"tasks": [task.model_dump(mode="json") for task in tasks]}
        if tool_name == "delete_task":
            ok = self.store.delete(parameters["id"])
            return {"deleted": ok}
        if tool_name == "delete_all_tasks":
            count = self.store.delete_all(status=parameters.get("status"))
            return {"deleted_count": count}
        return {"error": "unknown_tool"}
