from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_tools(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
