from __future__ import annotations

import re
from typing import Any


# Ordered from most-specific to most-general so the first match wins.
_KEYWORD_RULES: list[tuple[str, list[str], list[str]]] = [
    # (intent, must-contain-any, must-NOT-contain-any)
    ("calendar_create", ["创建日程", "新增日程", "安排会议", "安排日程", "添加会议", "提醒我"], []),
    ("calendar_query", ["日程", "会议", "calendar", "有什么安排", "有哪些安排"], []),
    ("task_create", ["创建任务", "新增任务", "添加任务", "新增待办", "帮我记录", "建一个任务"], []),
    ("task_update", ["完成任务", "标记完成", "任务完成", "关闭任务", "更新任务状态"], []),
    ("task_query", ["任务列表", "查任务", "有哪些任务", "待办", "todo"], []),
    ("email_draft", ["起草邮件", "写封邮件", "回复邮件", "草稿"], []),
    ("email_read", ["查邮件", "读邮件", "最新邮件", "邮件列表"], []),
    ("doc_search", ["搜索文档", "检索文档", "查找文档", "知识库", "规格书", "sop", "datasheet", "查一下资料"], []),
    ("entity_query", ["查一下", "告诉我关于", "这个人", "这家公司", "这个项目", "这个产品"], ["任务", "日程"]),
]

_INTENT_PROMPT = """你是一个意图分类器。从下列意图中选出与用户消息最匹配的一个，只输出意图名称，不含其他文字。

意图列表：
- calendar_create   创建/安排日程、会议、提醒
- calendar_query    查询/列出已有日程
- task_create       创建/新增任务、待办
- task_update       更新/完成/修改已有任务
- task_query        查询/列出任务
- email_read        读取/查询邮件
- email_draft       起草/回复邮件
- doc_search        搜索/检索文档或知识库
- entity_query      查询人物/公司/项目/产品信息
- general_qa        通用问答（技术问题、解释说明等）
- chitchat          闲聊"""

_VALID_INTENTS = {
    "calendar_create", "calendar_query",
    "task_create", "task_update", "task_query",
    "email_read", "email_draft",
    "doc_search", "entity_query",
    "general_qa", "chitchat",
}


class Planner:
    def classify_intent(self, message: str) -> str:
        """Fast keyword-based intent classification."""
        text = message.lower()
        for intent, must_have, must_not in _KEYWORD_RULES:
            if any(kw in text for kw in must_have) and not any(kw in text for kw in must_not):
                return intent
        return "general_qa"

    async def classify_intent_with_llm(self, message: str, llm: Any) -> str:
        """LLM-based intent classification with keyword fallback on failure."""
        from server.models import ChatMessage
        try:
            messages = [
                ChatMessage(role="system", content=_INTENT_PROMPT),
                ChatMessage(role="user", content=message),
            ]
            response = (await llm.chat(messages)).strip().lower()
            # Extract just the intent token (model may return extra spaces)
            match = re.search(r"[a-z_]+", response)
            intent = match.group() if match else ""
            if intent in _VALID_INTENTS:
                return intent
        except Exception:
            pass
        return self.classify_intent(message)
