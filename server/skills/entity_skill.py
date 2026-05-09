from __future__ import annotations

from typing import Any

from server.models import EntityCreate
from server.skills.base import BaseSkill
from server.storage.entity_store import EntityStore


class EntitySkill(BaseSkill):
    def __init__(self, store: EntityStore):
        self.store = store

    @property
    def name(self) -> str:
        return "entities"

    @property
    def description(self) -> str:
        return "JSON-backed entity creation and lookup"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_entity",
                    "description": "按类型和名称查询本地实体",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "enum": ["person", "company", "project", "product"],
                            },
                            "name": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_entity",
                    "description": "创建一个本地实体",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "enum": ["person", "company", "project", "product"],
                            },
                            "name": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["entity_type", "name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_entity",
                    "description": "更新实体的属性、标签或备注",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "enum": ["person", "company", "project", "product"],
                            },
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "notes": {"type": "string"},
                        },
                        "required": ["entity_type", "id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_entity",
                    "description": "删除指定实体（按 ID）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "enum": ["person", "company", "project", "product"],
                            },
                            "id": {"type": "string"},
                        },
                        "required": ["entity_type", "id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_entity_by_name",
                    "description": "按名称删除实体，不需要知道 ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "entity_type": {
                                "type": "string",
                                "enum": ["person", "company", "project", "product"],
                            },
                        },
                        "required": ["name"],
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "query_entity":
            entity_type = parameters.get("entity_type")
            name = parameters["name"]
            if entity_type:
                entity = self.store.find_by_name(entity_type, name)
                return {"entity": entity.model_dump(mode="json") if entity else None}
            matches = []
            for candidate_type in ["person", "company", "project", "product"]:
                entity = self.store.find_by_name(candidate_type, name)
                if entity:
                    matches.append(entity.model_dump(mode="json"))
            return {"matches": matches}

        if tool_name == "create_entity":
            entity_type = parameters.pop("entity_type")
            entity = self.store.create(entity_type, EntityCreate.model_validate(parameters))
            return entity.model_dump(mode="json")

        if tool_name == "update_entity":
            entity_type = parameters.pop("entity_type")
            entity_id = parameters.pop("id")
            updates: dict[str, Any] = {k: v for k, v in parameters.items() if v is not None}
            entity = self.store.update(entity_type, entity_id, updates)
            return entity.model_dump(mode="json") if entity else {"error": "entity_not_found"}

        if tool_name == "delete_entity":
            entity_type = parameters.pop("entity_type")
            entity_id = parameters["id"]
            ok = self.store.delete(entity_type, entity_id)
            return {"deleted": ok}

        if tool_name == "delete_entity_by_name":
            name = parameters["name"]
            entity_type = parameters.get("entity_type")
            search_types = [entity_type] if entity_type else ["person", "company", "project", "product"]
            deleted_names: list[str] = []
            for etype in search_types:
                entity = self.store.find_by_name(etype, name)
                if entity and self.store.delete(etype, entity.id):
                    deleted_names.append(entity.name)
            if deleted_names:
                return {"deleted": True, "names": deleted_names}
            return {"deleted": False, "error": f"未找到名为「{name}」的实体"}

        return {"error": "unknown_tool"}
