from __future__ import annotations

import re


# Ordered from most-specific to most-general; first match wins.
_KEYWORD_RULES: list[tuple[str, list[str], list[str]]] = [
    # (intent, must-contain-any, must-NOT-contain-any)
    ("calendar_create", [
        "创建日程", "新增日程", "安排会议", "安排日程", "添加会议", "添加日程",
        "提醒我", "帮我约", "预约", "排期",
    ], []),
    ("calendar_query", [
        "日程", "会议", "有什么安排", "有哪些安排", "这周安排", "今天安排",
    ], ["创建", "新增", "添加", "安排会议", "提醒我"]),
    ("task_create", [
        "创建任务", "新增任务", "添加任务", "新增待办", "帮我记录", "建一个任务",
        "加一条", "记一下", "记个任务",
    ], []),
    ("task_update", [
        "完成任务", "标记完成", "任务完成", "关闭任务", "更新任务", "任务状态",
    ], []),
    ("task_delete", [
        "删除任务", "删除所有任务", "删除全部任务", "清除任务", "清空任务",
        "删除所有待办", "删除已完成任务", "清除已完成",
    ], []),
    ("calendar_delete", [
        "删除日程", "删除会议", "删除所有日程", "删除全部日程",
        "清除日程", "清空日程", "取消会议",
    ], []),
    ("task_query", [
        "任务列表", "查任务", "有哪些任务", "待办", "todo", "还有什么任务",
    ], ["创建", "新增", "添加"]),
    ("email_draft", ["起草邮件", "写封邮件", "回复邮件", "写邮件", "发邮件"], []),
    ("email_read", ["查邮件", "读邮件", "最新邮件", "邮件列表", "有没有邮件"], []),
    ("doc_search", [
        "搜索文档", "检索文档", "查找文档", "知识库", "规格书", "sop",
        "datasheet", "查一下资料", "有没有资料", "工艺文件",
    ], []),
    ("entity_query", [
        "告诉我关于", "这个人", "这家公司", "这个项目", "这个产品",
        "荣创", "聚能", "博睿", "供应商信息",
    ], ["任务", "日程", "创建", "新增"]),
    ("general_qa", [
        "怎么", "如何", "为什么", "什么是", "解释", "分析", "建议",
        "共晶", "固晶", "焊线", "推力", "光衰", "可靠性", "esd", "vf",
        "lop", "cct", "显色", "支架", "荧光粉", "封装", "工艺",
    ], []),
]

_VALID_INTENTS = {
    "calendar_create", "calendar_query", "calendar_delete",
    "task_create", "task_update", "task_query", "task_delete",
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
