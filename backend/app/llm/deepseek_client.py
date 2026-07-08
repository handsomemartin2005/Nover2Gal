from __future__ import annotations

import json
import urllib.request
from typing import Any

from app.core.config import Settings


class DeepSeekClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build_chat_payload(self, messages: list[dict[str, str]], json_output: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": 0.3,
        }
        if json_output:
            payload["response_format"] = {"type": "json_object"}
            payload["thinking"] = {"type": "disabled"}
        return payload

    def chat(self, messages: list[dict[str, str]], json_output: bool = False) -> str:
        if not self.settings.llm_api_key:
            raise ValueError("LLM_API_KEY is required for DeepSeek chat calls")

        payload = json.dumps(self.build_chat_payload(messages, json_output=json_output)).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
