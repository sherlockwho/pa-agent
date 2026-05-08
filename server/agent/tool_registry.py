from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from server.skills.base import BaseSkill


@dataclass(frozen=True)
class ToolCall:
    name: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    name: str
    parameters: dict[str, Any]
    result: dict[str, Any]


class ToolRegistry:
    def __init__(self, skills: list[BaseSkill]):
        self.skills = skills
        self._tool_to_skill: dict[str, BaseSkill] = {}
        for skill in skills:
            for tool in skill.get_tools():
                name = tool.get("function", {}).get("name")
                if name:
                    self._tool_to_skill[name] = skill

    def tool_specs(self) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        for skill in self.skills:
            specs.extend(skill.get_tools())
        return specs

    async def execute(self, call: ToolCall) -> ToolResult:
        skill = self._tool_to_skill.get(call.name)
        if not skill:
            return ToolResult(call.name, call.parameters, {"error": "unknown_tool"})
        result = await skill.execute(call.name, dict(call.parameters))
        return ToolResult(call.name, call.parameters, result)

    async def execute_many(self, calls: list[ToolCall]) -> list[ToolResult]:
        results: list[ToolResult] = []
        for call in calls:
            results.append(await self.execute(call))
        return results
