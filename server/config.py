from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    auth_token: str | None = None


class LLMSettings(BaseModel):
    provider: str = "deepseek"
    api_key: str | None = None
    base_url: str = "https://api.deepseek.com"
    model_chat: str = "deepseek-chat"
    model_reasoner: str = "deepseek-reasoner"
    temperature: float = 0.7
    max_tokens: int = 4096


class EntitySettings(BaseModel):
    auto_extract: bool = True
    merge_threshold: float = 0.85


class EmbeddingSettings(BaseModel):
    model: str = "BAAI/bge-small-zh-v1.5"
    device: str = "cpu"
    batch_size: int = 32


class RAGSettings(BaseModel):
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5


class EmailSettings(BaseModel):
    imap_host: str | None = None
    imap_port: int = 993
    smtp_host: str | None = None
    smtp_port: int = 465
    username: str | None = None
    password: str | None = None


class MemorySettings(BaseModel):
    max_short_term_messages: int = 50
    daily_summary_trigger: int = 20
    weekly_summary_day: str = "sunday"


class Settings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    entity: EntitySettings = Field(default_factory=EntitySettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    data_dir: Path = Path("./data")


def _resolve_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env(item) for item in value]
    if isinstance(value, str):
        match = ENV_PATTERN.match(value)
        if match:
            return os.getenv(match.group(1))
    return value


def load_settings(config_path: str | Path = "config.yaml") -> Settings:
    path = Path(config_path)
    raw: dict[str, Any] = {}
    if path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    resolved = _resolve_env(raw)
    settings = Settings.model_validate(resolved)
    if not settings.data_dir.is_absolute():
        settings.data_dir = (path.parent / settings.data_dir).resolve()
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
