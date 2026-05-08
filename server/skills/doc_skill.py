from __future__ import annotations

from typing import Any

from server.rag.retriever import DocumentRetriever
from server.skills.base import BaseSkill


class DocSkill(BaseSkill):
    def __init__(self, retriever: DocumentRetriever):
        self.retriever = retriever

    @property
    def name(self) -> str:
        return "documents"

    @property
    def description(self) -> str:
        return "Local document search over the file-backed RAG index"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "在本地知识库中搜索相关文档片段",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "top_k": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if tool_name != "search_knowledge_base":
            return {"error": "unknown_tool"}
        results = self.retriever.search(parameters["query"], top_k=parameters.get("top_k"))
        return {"results": [result.model_dump(mode="json") for result in results]}
