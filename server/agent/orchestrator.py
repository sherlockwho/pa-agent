from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any

from server.agent.llm import DeepSeekClient
from server.agent.entity_modeler import EntityModeler
from server.agent.memory import ShortTermMemory
from server.agent.planner import Planner
from server.agent.tool_registry import ToolCall, ToolRegistry, ToolResult
from server.models import ChatMessage
from server.rag.retriever import DocumentRetriever
from server.skills.base import BaseSkill
from server.storage.calendar_store import CalendarStore
from server.storage.conversation_store import ConversationStore
from server.storage.entity_store import EntityStore
from server.storage.memory_store import MemoryStore
from server.storage.task_store import TaskStore


SYSTEM_PROMPT = """你是 Rory 的个人本地工作助理，主要协助 LED 封装工程、工艺文档、质量管理、供应商沟通、日程和任务管理。
回答使用中文，技术术语可以中英混用。你可以使用已注册工具创建任务、创建日程、检索知识库和查询实体；工具已执行时，请基于工具结果给出简洁确认或总结。"""


class Orchestrator:
    def __init__(
        self,
        llm: DeepSeekClient,
        memory: ShortTermMemory,
        conversations: ConversationStore,
        planner: Planner | None = None,
        task_store: TaskStore | None = None,
        calendar_store: CalendarStore | None = None,
        entity_store: EntityStore | None = None,
        document_retriever: DocumentRetriever | None = None,
        entity_modeler: EntityModeler | None = None,
        long_term_memory: MemoryStore | None = None,
        skills: list[BaseSkill] | None = None,
    ):
        self.llm = llm
        self.memory = memory
        self.conversations = conversations
        self.planner = planner or Planner()
        self.task_store = task_store
        self.calendar_store = calendar_store
        self.entity_store = entity_store
        self.document_retriever = document_retriever
        self.entity_modeler = entity_modeler
        self.long_term_memory = long_term_memory
        self.tools = ToolRegistry(skills or [])

    async def stream(self, message: str, session_id: str = "default") -> AsyncIterator[str]:
        user_message = ChatMessage(role="user", content=message)
        self.memory.append(session_id, user_message)
        self.conversations.append("user", message, session_id=session_id)

        if self.llm.settings.api_key:
            intent = await self.planner.classify_intent_with_llm(message, self.llm)
        else:
            intent = self.planner.classify_intent(message)
        local_context = self._build_local_context(intent, message)
        messages = [
            ChatMessage(role="system", content=f"{SYSTEM_PROMPT}\n\n当前意图分类：{intent}\n\n{local_context}"),
            *self.memory.get(session_id),
        ]

        tool_results = await self._run_tools_if_needed(message, messages)
        if tool_results:
            assistant_text = self._summarize_tool_results(tool_results)
            self.memory.append(session_id, ChatMessage(role="assistant", content=assistant_text))
            yield assistant_text
            await self._post_process(
                user_message=message,
                assistant_text=assistant_text,
                session_id=session_id,
                tools_called=[result.name for result in tool_results],
            )
            return

        chunks: list[str] = []
        async for chunk in self.llm.stream_chat(messages):
            chunks.append(chunk)
            yield chunk

        assistant_text = "".join(chunks)
        self.memory.append(session_id, ChatMessage(role="assistant", content=assistant_text))
        await self._post_process(
            user_message=message,
            assistant_text=assistant_text,
            session_id=session_id,
            tools_called=[],
        )

    # ------------------------------------------------------------------ #
    # Post-processing (runs after all tokens are streamed)                 #
    # ------------------------------------------------------------------ #

    async def _post_process(
        self,
        user_message: str,
        assistant_text: str,
        session_id: str,
        tools_called: list[str],
    ) -> None:
        extracted_entities = await self._extract_entities_async(user_message)
        self.conversations.append(
            "assistant",
            assistant_text,
            session_id=session_id,
            entities_extracted=extracted_entities,
            tools_called=tools_called,
        )
        await self._refresh_daily_memory_async()

    async def _extract_entities_async(self, message: str) -> list[str]:
        if not self.entity_modeler:
            return []
        records = await self.entity_modeler.upsert_entities_async(message, self.llm)
        return [record.id for record in records]

    async def _refresh_daily_memory_async(self) -> None:
        if self.long_term_memory:
            await self.long_term_memory.update_daily_summary_with_llm(llm=self.llm)

    # ------------------------------------------------------------------ #
    # Tool dispatch                                                        #
    # ------------------------------------------------------------------ #

    async def _run_tools_if_needed(self, message: str, messages: list[ChatMessage]) -> list[ToolResult]:
        local_calls = self._infer_local_tool_calls(message)
        if local_calls:
            return await self.tools.execute_many(local_calls)

        if not self.llm.settings.api_key or not self.tools.tool_specs():
            return []

        raw_messages = [chat_message.model_dump() for chat_message in messages]
        tool_message = await self.llm.chat_with_tools(raw_messages, self.tools.tool_specs())
        calls = self._parse_llm_tool_calls(tool_message)
        if not calls:
            return []
        return await self.tools.execute_many(calls)

    def _infer_local_tool_calls(self, message: str) -> list[ToolCall]:
        normalized = message.strip()
        calls: list[ToolCall] = []

        if self._looks_like_task_create(normalized):
            title = self._extract_after_keywords(normalized, ["任务", "待办"])
            title = re.sub(r"^(创建|新增|添加|帮我|请|一个|一条|：|:|\s)+", "", title).strip()
            title = re.sub(r"(截止|due)[:：]?\s*\d{4}-\d{1,2}-\d{1,2}.*$", "", title, flags=re.IGNORECASE).strip()
            if title:
                params: dict[str, Any] = {"title": title}
                due_date = self._extract_date(normalized)
                if due_date:
                    params["due_date"] = due_date
                calls.append(ToolCall("create_task", params))
                return calls

        if self._looks_like_calendar_create(normalized):
            title = self._extract_after_keywords(normalized, ["日程", "会议", "提醒"])
            title = re.sub(r"^(创建|新增|添加|安排|帮我|请|一个|一条|：|:|\s)+", "", title).strip()
            title = self._strip_datetime_text(title)
            start_time = self._extract_datetime(normalized)
            if title and start_time:
                end_time = (datetime.fromisoformat(start_time) + timedelta(hours=1)).isoformat()
                calls.append(
                    ToolCall(
                        "create_calendar_event",
                        {
                            "title": title,
                            "start_time": start_time,
                            "end_time": end_time,
                            "description": normalized,
                        },
                    )
                )
                return calls

        if self._looks_like_doc_search(normalized):
            query = self._extract_after_keywords(normalized, ["搜索", "检索", "查找", "查询"])
            calls.append(ToolCall("search_knowledge_base", {"query": query or normalized, "top_k": 5}))
            return calls

        return calls

    def _parse_llm_tool_calls(self, message: dict[str, Any]) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            name = function.get("name")
            raw_args = function.get("arguments") or "{}"
            if not name:
                continue
            try:
                parameters = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                parameters = {}
            calls.append(ToolCall(name, parameters))
        return calls

    def _summarize_tool_results(self, results: list[ToolResult]) -> str:
        lines = []
        for result in results:
            if result.result.get("error"):
                lines.append(f"{result.name} 执行失败：{result.result['error']}")
                continue
            if result.name == "create_task":
                lines.append(f"已创建任务：{result.result.get('title')}")
            elif result.name == "create_calendar_event":
                lines.append(f"已创建日程：{result.result.get('title')}，时间 {result.result.get('start_time')}")
            elif result.name == "search_knowledge_base":
                items = result.result.get("results", [])
                if not items:
                    lines.append("本地知识库没有检索到相关片段。")
                else:
                    lines.append("本地知识库检索结果：")
                    for index, item in enumerate(items[:5], start=1):
                        chunk = item.get("chunk", {})
                        lines.append(
                            f"{index}. {chunk.get('source_file')}#{chunk.get('position')}: "
                            f"{chunk.get('text', '')[:160]}"
                        )
            elif result.name == "query_entity":
                lines.append("实体查询完成：" + json.dumps(result.result, ensure_ascii=False))
            else:
                lines.append(f"{result.name} 执行完成。")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Intent helpers                                                       #
    # ------------------------------------------------------------------ #

    def _looks_like_task_create(self, text: str) -> bool:
        return any(w in text for w in ["创建", "新增", "添加", "记录", "建"]) and any(
            w in text for w in ["任务", "待办"]
        )

    def _looks_like_calendar_create(self, text: str) -> bool:
        return any(w in text for w in ["创建", "新增", "添加", "安排", "提醒"]) and any(
            w in text for w in ["日程", "会议", "提醒"]
        )

    def _looks_like_doc_search(self, text: str) -> bool:
        return any(w in text for w in ["搜索", "检索", "查找", "查询"]) and any(
            w in text for w in ["文档", "资料", "知识库", "规格书", "SOP", "Datasheet"]
        )

    def _extract_after_keywords(self, text: str, keywords: list[str]) -> str:
        for keyword in keywords:
            if keyword in text:
                return text.split(keyword, 1)[1].strip(" ：:")
        return text

    def _extract_date(self, text: str) -> str | None:
        match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", text)
        if match:
            return match.group(1)
        today = datetime.now().astimezone().date()
        if "今天" in text:
            return today.isoformat()
        if "明天" in text:
            return (today + timedelta(days=1)).isoformat()
        return None

    def _extract_datetime(self, text: str) -> str | None:
        match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})[ T日]*(\d{1,2})(?::|点)(\d{1,2})?", text)
        if match:
            date_part = match.group(1)
            hour = int(match.group(2))
            minute = int(match.group(3) or 0)
            return datetime.fromisoformat(date_part).replace(hour=hour, minute=minute).astimezone().isoformat()
        date_value = self._extract_date(text)
        hour_match = re.search(r"(\d{1,2})(?::|点)(\d{1,2})?", text)
        if date_value and hour_match:
            hour = int(hour_match.group(1))
            minute = int(hour_match.group(2) or 0)
            return datetime.fromisoformat(date_value).replace(hour=hour, minute=minute).astimezone().isoformat()
        return None

    def _strip_datetime_text(self, text: str) -> str:
        text = re.sub(r"\d{4}-\d{1,2}-\d{1,2}[ T日]*(\d{1,2}(:|点)\d{0,2})?", "", text)
        text = re.sub(r"(今天|明天)?\s*\d{1,2}(:|点)\d{0,2}", "", text)
        return text.strip(" ，,。")

    def _build_local_context(self, intent: str, message: str) -> str:
        if intent == "doc_search" and self.document_retriever:
            results = self.document_retriever.search(message)
            if not results:
                return "本地知识库暂未检索到相关片段。"
            lines = ["本地知识库检索结果："]
            for index, result in enumerate(results, start=1):
                lines.append(
                    f"{index}. {result.chunk.source_file}#{result.chunk.position} "
                    f"(score={result.score:.2f}): {result.chunk.text[:300]}"
                )
            return "\n".join(lines)

        if intent == "task_query" and self.task_store:
            tasks = self.task_store.list()
            if not tasks:
                return "当前本地任务列表为空。"
            lines = ["本地任务摘要："]
            for task in tasks[:20]:
                due = f"，截止 {task.due_date}" if task.due_date else ""
                lines.append(f"- [{task.status}] {task.title}{due}")
            return "\n".join(lines)

        if intent == "calendar_query" and self.calendar_store:
            events = self.calendar_store.list()
            if not events:
                return "当前默认日历没有事件。"
            lines = ["默认日历近期事件："]
            for event in events[:20]:
                lines.append(f"- {event.start_time.isoformat()} {event.title}")
            return "\n".join(lines)

        if intent == "entity_query" and self.entity_store:
            lines = ["本地实体摘要："]
            for entity_type in ["person", "company", "project", "product"]:
                entities = self.entity_store.list(entity_type)[:10]
                if entities:
                    names = "、".join(entity.name for entity in entities)
                    lines.append(f"- {entity_type}: {names}")
            return "\n".join(lines) if len(lines) > 1 else "当前本地实体库为空。"

        if self.long_term_memory:
            return self.long_term_memory.build_context(days=3)

        return "没有额外本地上下文。"
