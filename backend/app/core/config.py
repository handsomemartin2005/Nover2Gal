from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    app_env: str
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    embedding_dim: int
    max_chunk_chars: int
    chunk_overlap_chars: int
    max_retrieved_chunks: int
    enable_lightrag: bool
    enable_auto_revision: bool
    max_auto_revision_rounds: int
    image_provider: str
    image_base_url: str
    image_api_key: str
    image_model: str
    tts_provider: str
    tts_base_url: str
    tts_api_key: str
    tts_model: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        source = os.environ if env is None else env

        return cls(
            app_env=_get(source, "APP_ENV", "dev"),
            llm_provider=_get(source, "LLM_PROVIDER", "deepseek"),
            llm_base_url=_get(source, "LLM_BASE_URL", "https://api.deepseek.com"),
            llm_api_key=_get(source, "LLM_API_KEY", _get(source, "DEEPSEEK_API", "")),
            llm_model=_get(source, "LLM_MODEL", "deepseek-v4-pro"),
            embedding_provider=_get(source, "EMBEDDING_PROVIDER", "deepseek"),
            embedding_model=_get(source, "EMBEDDING_MODEL", "deepseek-v4-pro"),
            embedding_dim=_get_int(source, "EMBEDDING_DIM", 1536),
            max_chunk_chars=_get_int(source, "MAX_CHUNK_CHARS", 1500),
            chunk_overlap_chars=_get_int(source, "CHUNK_OVERLAP_CHARS", 200),
            max_retrieved_chunks=_get_int(source, "MAX_RETRIEVED_CHUNKS", 8),
            enable_lightrag=_get_bool(source, "ENABLE_LIGHTRAG", False),
            enable_auto_revision=_get_bool(source, "ENABLE_AUTO_REVISION", True),
            max_auto_revision_rounds=_get_int(source, "MAX_AUTO_REVISION_ROUNDS", 1),
            image_provider=_get(source, "IMAGE_PROVIDER", "glm"),
            image_base_url=_get(source, "IMAGE_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/images/generations"),
            image_api_key=_get(source, "IMAGE_API_KEY", _get(source, "GLM_API_KEY", "")),
            image_model=_get(source, "IMAGE_MODEL", "cogview-4"),
            tts_provider=_get(source, "TTS_PROVIDER", "openai-compatible"),
            tts_base_url=_get(source, "TTS_BASE_URL", ""),
            tts_api_key=_get(source, "TTS_API_KEY", ""),
            tts_model=_get(source, "TTS_MODEL", ""),
        )


def _get(source: Mapping[str, str], key: str, default: str) -> str:
    value = source.get(key)
    return default if value is None or value == "" else value


def _get_int(source: Mapping[str, str], key: str, default: int) -> int:
    value = _get(source, key, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc


def _get_bool(source: Mapping[str, str], key: str, default: bool) -> bool:
    value = source.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
