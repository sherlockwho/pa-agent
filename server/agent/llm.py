from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from server.config import LLMSettings
from server.models import ChatMessage


class DeepSeekClient:
    def __init__(self, settings: LLMSettings):
        self.settings = settings

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        if not self.settings.api_key:
            yield self._offline_reply(messages)
            return

        payload: dict[str, Any] = {
            "model": self.settings.model_chat,
            "messages": [message.model_dump() for message in messages],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self.settings.api_key}"}
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    token = self._extract_stream_delta(data)
                    if token:
                        yield token

    async def chat(self, messages: list[ChatMessage]) -> str:
        chunks: list[str] = []
        async for chunk in self.stream_chat(messages):
            chunks.append(chunk)
        return "".join(chunks)

    async def chat_with_tools(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.settings.api_key:
            return {"role": "assistant", "content": self._offline_reply_from_raw(messages)}

        payload: dict[str, Any] = {
            "model": self.settings.model_chat,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.settings.api_key}"}
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return {"role": "assistant", "content": ""}
        return choices[0].get("message") or {"role": "assistant", "content": ""}

    def _offline_reply(self, messages: list[ChatMessage]) -> str:
        last_user = next((message.content for message in reversed(messages) if message.role == "user"), "")
        return self._offline_reply_text(last_user)

    def _offline_reply_from_raw(self, messages: list[dict[str, Any]]) -> str:
        last_user = next((str(message.get("content", "")) for message in reversed(messages) if message.get("role") == "user"), "")
        return self._offline_reply_text(last_user)

    def _offline_reply_text(self, last_user: str) -> str:
        return (
            "我已经收到你的消息。当前未配置 DEEPSEEK_API_KEY，"
            f"所以先以本地开发模式记录对话：{last_user}"
        )

    def _extract_stream_delta(self, data: str) -> str:
        import json

        payload = json.loads(data)
        choices = payload.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("delta", {}).get("content") or ""
