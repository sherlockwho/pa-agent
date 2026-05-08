from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from server.models import ChatMessage


class ShortTermMemory:
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self._sessions: dict[str, deque[ChatMessage]] = defaultdict(lambda: deque(maxlen=max_messages))

    def append(self, session_id: str, message: ChatMessage) -> None:
        self._sessions[session_id].append(message)

    def get(self, session_id: str) -> list[ChatMessage]:
        return list(self._sessions[session_id])

    def extend(self, session_id: str, messages: Iterable[ChatMessage]) -> None:
        for message in messages:
            self.append(session_id, message)
