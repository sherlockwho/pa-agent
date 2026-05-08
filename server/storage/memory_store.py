from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from server.models import ChatMessage, ConversationRecord, MemorySummary
from server.storage.conversation_store import ConversationStore
from server.storage.file_store import FileStore


_DAILY_NARRATIVE_PROMPT = (
    "你是一个记忆摘要助手。根据今天的对话，生成一段简洁的中文摘要（100字以内），"
    "描述今天主要讨论的话题、完成的任务或重要决策。只输出摘要文字，不含其他格式。"
)

_WEEKLY_NARRATIVE_PROMPT = (
    "你是一个记忆摘要助手。根据过去一周的每日摘要，生成一段中文周报摘要（200字以内），"
    "包括：本周核心工作、完成的重要任务、遇到的问题、下周需关注的事项。"
    "只输出摘要文字，不含其他格式。"
)


class MemoryStore:
    def __init__(self, file_store: FileStore, conversations: ConversationStore):
        self.file_store = file_store
        self.conversations = conversations

    # ------------------------------------------------------------------ #
    # Paths                                                                #
    # ------------------------------------------------------------------ #

    def summary_path(self, day: str) -> Path:
        return self.file_store.data_dir / "memory" / f"{day}.yaml"

    def weekly_summary_path(self, week_start: str) -> Path:
        return self.file_store.data_dir / "memory" / f"week-{week_start}.yaml"

    def global_summary_path(self) -> Path:
        return self.file_store.data_dir / "memory" / "summary.yaml"

    # ------------------------------------------------------------------ #
    # Daily summary                                                        #
    # ------------------------------------------------------------------ #

    def load_daily_summary(self, day: str) -> MemorySummary | None:
        path = self.summary_path(day)
        if not path.exists():
            return None
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return MemorySummary.model_validate(payload)

    def list_daily_summaries(self) -> list[MemorySummary]:
        summaries: list[MemorySummary] = []
        for path in sorted((self.file_store.data_dir / "memory").glob("[0-9]*.yaml")):
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            summaries.append(MemorySummary.model_validate(payload))
        return summaries

    async def update_daily_summary_with_llm(self, day: str | None = None, llm: Any | None = None) -> MemorySummary:
        """Build the daily summary, optionally enriching it with an LLM-generated narrative."""
        target = day or datetime.now().astimezone().date().isoformat()
        records = self._load_conversation_records(target)

        tools = sorted({tool for record in records for tool in record.tools_called})
        entities = sorted({entity for record in records for entity in record.entities_extracted})
        highlights = self._extract_highlights(records)

        narrative = ""
        if llm and records:
            narrative = await self._generate_narrative(records, llm, _DAILY_NARRATIVE_PROMPT)

        summary = MemorySummary(
            date=target,
            message_count=len(records),
            user_message_count=sum(1 for r in records if r.role == "user"),
            assistant_message_count=sum(1 for r in records if r.role == "assistant"),
            tools_called=tools,
            entities_mentioned=entities,
            highlights=highlights,
            narrative=narrative,
            updated_at=datetime.now().astimezone(),
        )
        self._write_yaml(self.summary_path(target), summary.model_dump(mode="json"))
        self.update_global_summary()
        return summary

    def update_daily_summary(self, day: str | None = None) -> MemorySummary:
        """Sync convenience wrapper (no LLM narrative)."""
        import asyncio
        try:
            asyncio.get_running_loop()
            asyncio.ensure_future(self.update_daily_summary_with_llm(day=day))
            return MemorySummary(
                date=day or datetime.now().astimezone().date().isoformat(),
                updated_at=datetime.now().astimezone(),
            )
        except RuntimeError:
            return asyncio.run(self.update_daily_summary_with_llm(day=day))

    # ------------------------------------------------------------------ #
    # Weekly summary                                                       #
    # ------------------------------------------------------------------ #

    async def generate_weekly_summary(self, week_start: str | None = None, llm: Any | None = None) -> dict:
        """Summarise the 7 days starting from week_start (ISO date, defaults to last Monday)."""
        if week_start is None:
            today = datetime.now().astimezone().date()
            week_start = (today - timedelta(days=today.weekday())).isoformat()

        start = datetime.fromisoformat(week_start).date()
        days = [(start + timedelta(days=i)).isoformat() for i in range(7)]

        daily_summaries = [self.load_daily_summary(d) for d in days]
        present = [s for s in daily_summaries if s is not None]

        tool_counts = Counter(tool for s in present for tool in s.tools_called)
        entity_counts = Counter(e for s in present for e in s.entities_mentioned)
        all_highlights = [h for s in present for h in s.highlights[:3]]

        narrative = ""
        if llm and present:
            day_texts = []
            for s in present:
                if s.narrative:
                    day_texts.append(f"{s.date}: {s.narrative}")
                elif s.highlights:
                    day_texts.append(f"{s.date}: " + "；".join(s.highlights[:2]))
            if day_texts:
                context = "\n".join(day_texts)
                from server.models import ChatMessage
                messages = [
                    ChatMessage(role="system", content=_WEEKLY_NARRATIVE_PROMPT),
                    ChatMessage(role="user", content=f"本周每日摘要：\n{context}"),
                ]
                try:
                    narrative = await llm.chat(messages)
                except Exception:
                    pass

        payload = {
            "week_start": week_start,
            "days_covered": len(present),
            "total_messages": sum(s.message_count for s in present),
            "top_tools": dict(tool_counts.most_common(10)),
            "top_entities": dict(entity_counts.most_common(20)),
            "highlights": all_highlights[-15:],
            "narrative": narrative,
            "updated_at": datetime.now().astimezone().isoformat(),
        }
        self._write_yaml(self.weekly_summary_path(week_start), payload)
        return payload

    def load_weekly_summary(self, week_start: str) -> dict | None:
        path = self.weekly_summary_path(week_start)
        if not path.exists():
            return None
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def list_weekly_summaries(self) -> list[dict]:
        result: list[dict] = []
        for path in sorted((self.file_store.data_dir / "memory").glob("week-*.yaml")):
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            result.append(payload)
        return result

    # ------------------------------------------------------------------ #
    # Global summary                                                       #
    # ------------------------------------------------------------------ #

    def update_global_summary(self) -> dict:
        summaries = self.list_daily_summaries()
        tool_counts = Counter(tool for summary in summaries for tool in summary.tools_called)
        entity_counts = Counter(entity for summary in summaries for entity in summary.entities_mentioned)
        payload = {
            "updated_at": datetime.now().astimezone().isoformat(),
            "days_summarized": len(summaries),
            "recent_highlights": [
                highlight
                for summary in summaries[-7:]
                for highlight in summary.highlights[:3]
            ][-12:],
            "top_tools": dict(tool_counts.most_common(10)),
            "top_entities": dict(entity_counts.most_common(20)),
        }
        self._write_yaml(self.global_summary_path(), payload)
        return payload

    # ------------------------------------------------------------------ #
    # Context for system prompt                                            #
    # ------------------------------------------------------------------ #

    def build_context(self, days: int = 3) -> str:
        summaries = self.list_daily_summaries()[-days:]
        if not summaries:
            return "暂无长期记忆摘要。"
        lines = ["长期记忆摘要："]
        for summary in summaries:
            lines.append(f"- {summary.date}: {summary.message_count} 条消息")
            if summary.narrative:
                lines.append(f"  摘要：{summary.narrative}")
            else:
                for highlight in summary.highlights[:3]:
                    lines.append(f"  - {highlight}")
            if summary.entities_mentioned:
                lines.append("  - 提及实体: " + "、".join(summary.entities_mentioned[:8]))
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _generate_narrative(
        self, records: list[ConversationRecord], llm: Any, system_prompt: str
    ) -> str:
        user_messages = [r.content for r in records if r.role == "user"][-10:]
        if not user_messages:
            return ""
        conversation_text = "\n".join(f"- {msg[:200]}" for msg in user_messages)
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=f"对话内容：\n{conversation_text}"),
        ]
        try:
            return await llm.chat(messages)
        except Exception:
            return ""

    def _load_conversation_records(self, day: str) -> list[ConversationRecord]:
        path = self.file_store.data_dir / "conversations" / f"{day}.jsonl"
        if not path.exists():
            return []
        records: list[ConversationRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(ConversationRecord.model_validate(json.loads(line)))
        return records

    def _extract_highlights(self, records: list[ConversationRecord]) -> list[str]:
        highlights: list[str] = []
        for record in records:
            if record.role != "user":
                continue
            text = record.content.strip()
            if not text:
                continue
            if any(kw in text for kw in ["任务", "日程", "会议", "项目", "LED", "SOP", "规格书", "供应商"]):
                highlights.append(text[:160])
        return highlights[-12:]

    def _write_yaml(self, path: Path, payload: dict) -> None:
        text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        self.file_store.write_text(path, text)
