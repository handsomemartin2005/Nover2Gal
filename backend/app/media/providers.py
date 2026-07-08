from __future__ import annotations

from typing import Any

from app.core.config import Settings


IMAGE_PROVIDER_CANDIDATES = [
    {
        "provider": "glm",
        "model_examples": ["cogview-4", "cogview-4-250304"],
        "use_for": "Chinese prompt image generation, scene backgrounds, character concept art",
        "env": ["IMAGE_PROVIDER=glm", "GLM_API_KEY or IMAGE_API_KEY", "IMAGE_MODEL=cogview-4"],
    },
    {
        "provider": "openai-compatible",
        "model_examples": ["provider-specific-image-model"],
        "use_for": "Any OpenAI-compatible image endpoint supplied by the user",
        "env": ["IMAGE_PROVIDER=openai-compatible", "IMAGE_BASE_URL", "IMAGE_API_KEY", "IMAGE_MODEL"],
    },
]

TTS_PROVIDER_CANDIDATES = [
    {
        "provider": "openai-compatible",
        "model_examples": ["provider-specific-tts-model"],
        "use_for": "Cheap domestic TTS providers that expose OpenAI-like audio APIs",
        "env": ["TTS_PROVIDER=openai-compatible", "TTS_BASE_URL", "TTS_API_KEY", "TTS_MODEL"],
    },
    {
        "provider": "volcengine/minimax/qwen",
        "model_examples": ["provider-specific-voice-model"],
        "use_for": "Future native adapters for Chinese voice synthesis",
        "env": ["TTS_PROVIDER", "TTS_API_KEY", "TTS_MODEL"],
    },
]


def provider_status(settings: Settings) -> dict[str, Any]:
    return {
        "image": {
            "configured": bool(settings.image_api_key and settings.image_base_url and settings.image_model),
            "provider": settings.image_provider,
            "base_url": _masked_url(settings.image_base_url),
            "model": settings.image_model,
            "candidates": IMAGE_PROVIDER_CANDIDATES,
        },
        "tts": {
            "configured": bool(settings.tts_api_key and settings.tts_base_url and settings.tts_model),
            "provider": settings.tts_provider,
            "base_url": _masked_url(settings.tts_base_url),
            "model": settings.tts_model,
            "candidates": TTS_PROVIDER_CANDIDATES,
        },
    }


def build_image_generation_plan(prompt: str, scene_id: str, style: str, settings: Settings) -> dict[str, Any]:
    return {
        "configured": bool(settings.image_api_key and settings.image_base_url and settings.image_model),
        "provider": settings.image_provider,
        "model": settings.image_model,
        "scene_id": scene_id,
        "style": style,
        "prompt": prompt,
        "request_shape": {
            "model": settings.image_model,
            "prompt": prompt,
            "size": "1280x720",
        },
        "note": "This endpoint returns the generation plan first. Enable a concrete provider adapter before spending image tokens.",
    }


def build_tts_plan(text: str, voice: str, settings: Settings) -> dict[str, Any]:
    return {
        "configured": bool(settings.tts_api_key and settings.tts_base_url and settings.tts_model),
        "provider": settings.tts_provider,
        "model": settings.tts_model,
        "voice": voice,
        "text": text,
        "request_shape": {
            "model": settings.tts_model,
            "voice": voice,
            "input": text,
            "format": "mp3",
        },
        "note": "This endpoint returns the synthesis plan first. Add a concrete provider adapter before spending TTS tokens.",
    }


def _masked_url(value: str) -> str:
    return value if value else ""
