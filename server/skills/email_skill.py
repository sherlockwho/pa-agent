from __future__ import annotations

import imaplib
from email.header import decode_header
from email.message import Message
from email.parser import BytesParser
from email.policy import default
from typing import Any

from server.config import EmailSettings
from server.skills.base import BaseSkill


class EmailSkill(BaseSkill):
    def __init__(self, settings: EmailSettings):
        self.settings = settings

    @property
    def name(self) -> str:
        return "email"

    @property
    def description(self) -> str:
        return "IMAP email reading and draft helper"

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_recent_emails",
                    "description": "读取最近 N 封邮件的元信息",
                    "parameters": {
                        "type": "object",
                        "properties": {"limit": {"type": "integer", "default": 5}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "draft_email_reply",
                    "description": "根据上下文起草邮件回复，不发送",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {"type": "string"},
                            "subject": {"type": "string"},
                            "context": {"type": "string"},
                        },
                        "required": ["recipient", "subject", "context"],
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "read_recent_emails":
            return {"emails": self.read_recent(limit=int(parameters.get("limit", 5)))}
        if tool_name == "draft_email_reply":
            return {
                "draft": {
                    "to": parameters["recipient"],
                    "subject": "Re: " + parameters["subject"].removeprefix("Re: "),
                    "body": self._draft_body(parameters["context"]),
                }
            }
        return {"error": "unknown_tool"}

    def read_recent(self, limit: int = 5) -> list[dict[str, str]]:
        self._ensure_configured()
        with imaplib.IMAP4_SSL(self.settings.imap_host, self.settings.imap_port) as client:
            client.login(self.settings.username, self.settings.password)
            client.select("INBOX")
            _, data = client.search(None, "ALL")
            ids = data[0].split()[-limit:]
            emails: list[dict[str, str]] = []
            for message_id in reversed(ids):
                _, msg_data = client.fetch(message_id, "(RFC822)")
                message = BytesParser(policy=default).parsebytes(msg_data[0][1])
                emails.append(self._summarize_message(message))
            return emails

    def _ensure_configured(self) -> None:
        missing = [
            key
            for key in ["imap_host", "username", "password"]
            if not getattr(self.settings, key)
        ]
        if missing:
            raise RuntimeError("Email is not configured: " + ", ".join(missing))

    def _summarize_message(self, message: Message) -> dict[str, str]:
        return {
            "from": str(message.get("from", "")),
            "subject": self._decode(str(message.get("subject", ""))),
            "date": str(message.get("date", "")),
        }

    def _decode(self, value: str) -> str:
        parts = []
        for text, encoding in decode_header(value):
            if isinstance(text, bytes):
                parts.append(text.decode(encoding or "utf-8", errors="ignore"))
            else:
                parts.append(text)
        return "".join(parts)

    def _draft_body(self, context: str) -> str:
        return f"您好，\n\n关于您提到的事项，我这边初步回复如下：\n\n{context}\n\n谢谢。"
