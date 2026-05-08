from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from server.models import ChatMessage, EntityCreate, EntityRecord, EntityType
from server.storage.entity_store import EntityStore


ENTITY_EXTRACT_PROMPT = """你是一个实体提取助手。从用户消息中提取实体，输出 JSON 数组。

实体类型：
- person: 人名、职位、所属组织
- company: 公司名（供应商/客户/合作伙伴）
- project: 项目名、状态、里程碑
- product: 产品名、型号、规格参数

输出格式示例：
[{"type":"person","name":"张工","attributes":{"role":"供应商技术支持"},"context":"张工说芯片下周到货"}]

规则：
- 只提取明确信息，不推测
- 产品型号完整提取（"3535 UVC LED"而非"LED"）
- 无实体时返回 []
- 只输出 JSON 数组，不含任何其他文字"""


@dataclass(frozen=True)
class ExtractedEntity:
    entity_type: EntityType
    payload: EntityCreate


class EntityModeler:
    def __init__(self, store: EntityStore):
        self.store = store

    # ------------------------------------------------------------------ #
    # Public async interface (used by Orchestrator post-processing)        #
    # ------------------------------------------------------------------ #

    async def upsert_entities_async(self, text: str, llm: Any | None = None) -> list[EntityRecord]:
        """Extract entities and upsert them.  Uses LLM when available, regex fallback."""
        if llm and getattr(llm.settings, "api_key", None):
            candidates = await self._extract_with_llm(text, llm)
        else:
            candidates = self.extract_lightweight(text)
        return self._upsert_candidates(candidates, text)

    # ------------------------------------------------------------------ #
    # Sync legacy interface (kept for backward compat)                     #
    # ------------------------------------------------------------------ #

    def upsert_extracted_entities(self, text: str) -> list[EntityRecord]:
        return self._upsert_candidates(self.extract_lightweight(text), text)

    # ------------------------------------------------------------------ #
    # LLM extraction                                                       #
    # ------------------------------------------------------------------ #

    async def _extract_with_llm(self, text: str, llm: Any) -> list[ExtractedEntity]:
        try:
            messages = [
                ChatMessage(role="system", content=ENTITY_EXTRACT_PROMPT),
                ChatMessage(role="user", content=text),
            ]
            response = await llm.chat(messages)
            json_match = re.search(r"\[.*?\]", response, re.DOTALL)
            if not json_match:
                return self.extract_lightweight(text)
            items: list[dict[str, Any]] = json.loads(json_match.group())
            candidates: list[ExtractedEntity] = []
            for item in items:
                entity_type = item.get("type", "")
                name = (item.get("name") or "").strip()
                if not name or entity_type not in {"person", "company", "project", "product"}:
                    continue
                attrs: dict[str, Any] = dict(item.get("attributes") or {})
                attrs["source"] = "llm_extract"
                context = str(item.get("context") or text[:200])
                candidates.append(
                    ExtractedEntity(
                        entity_type=entity_type,
                        payload=EntityCreate(
                            name=name,
                            attributes=attrs,
                            notes=[{"content": context[:300]}],
                        ),
                    )
                )
            result = self._dedupe(candidates)
            return result if result else self.extract_lightweight(text)
        except Exception:
            return self.extract_lightweight(text)

    # ------------------------------------------------------------------ #
    # Regex lightweight extraction (fallback)                              #
    # ------------------------------------------------------------------ #

    def extract_lightweight(self, text: str) -> list[ExtractedEntity]:
        candidates: list[ExtractedEntity] = []
        candidates.extend(self._extract_people(text))
        candidates.extend(self._extract_products(text))
        candidates.extend(self._extract_companies(text))
        candidates.extend(self._extract_projects(text))
        return self._dedupe(candidates)

    def _extract_people(self, text: str) -> list[ExtractedEntity]:
        people: list[ExtractedEntity] = []
        for match in re.finditer(
            r"(?<![一-鿿])([一-鿿]{1,4}(?:工|经理|主管|博士|老师))(?![一-鿿])",
            text,
        ):
            people.append(self._candidate("person", match.group(1), text))
        return people

    def _extract_products(self, text: str) -> list[ExtractedEntity]:
        products: list[ExtractedEntity] = []
        for match in re.finditer(
            r"([0-9A-Za-z][0-9A-Za-z +\-_/]{1,48}\s*LED)(?:项目|产品|方案)?",
            text,
            flags=re.IGNORECASE,
        ):
            name = re.sub(r"\s+", " ", match.group(1)).strip()
            products.append(self._candidate("product", name, text))
        return products

    def _extract_companies(self, text: str) -> list[ExtractedEntity]:
        companies: list[ExtractedEntity] = []
        for match in re.finditer(
            r"([一-鿿A-Za-z0-9]{2,32}(?:公司|科技|半导体|电子))(?![一-鿿])",
            text,
        ):
            companies.append(self._candidate("company", match.group(1), text))
        return companies

    def _extract_projects(self, text: str) -> list[ExtractedEntity]:
        projects: list[ExtractedEntity] = []
        for match in re.finditer(
            r"([一-鿿A-Za-z0-9 +\-_/]{2,48}项目)(?![一-鿿])",
            text,
        ):
            name = re.sub(r"^[说讲提到关于]+", "", match.group(1)).strip()
            if name:
                projects.append(self._candidate("project", name, text))
        return projects

    def _candidate(self, entity_type: EntityType, name: str, source_text: str) -> ExtractedEntity:
        return ExtractedEntity(
            entity_type=entity_type,
            payload=EntityCreate(
                name=name.strip(),
                attributes={"source": "lightweight_regex"},
                notes=[{"content": source_text[:200]}],
            ),
        )

    def _dedupe(self, candidates: list[ExtractedEntity]) -> list[ExtractedEntity]:
        seen: set[tuple[str, str]] = set()
        unique: list[ExtractedEntity] = []
        for candidate in candidates:
            key = (candidate.entity_type, candidate.payload.name.lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    # ------------------------------------------------------------------ #
    # Store upsert                                                         #
    # ------------------------------------------------------------------ #

    def _upsert_candidates(self, candidates: list[ExtractedEntity], text: str) -> list[EntityRecord]:
        records: list[EntityRecord] = []
        for candidate in candidates:
            existing = self.store.find_by_name(candidate.entity_type, candidate.payload.name)
            if existing:
                updated = self.store.update(
                    candidate.entity_type,
                    existing.id,
                    {
                        "mention_count": existing.mention_count + 1,
                        "notes": [*existing.notes, *candidate.payload.notes],
                    },
                )
                if updated:
                    records.append(updated)
            else:
                records.append(self.store.create(candidate.entity_type, candidate.payload))
        return records
