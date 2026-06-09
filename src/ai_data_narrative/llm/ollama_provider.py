"""Ollama local LLM provider."""
from __future__ import annotations

import json
from typing import Any, Dict, List

import requests

from ai_data_narrative.config import OLLAMA_BASE_URL
from ai_data_narrative.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    name: str = "ollama"
    weight: float = 0.5

    def __init__(self, base_url: str | None = None, model: str = "llama3"):
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.model = model

    def complete(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> str | Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        if json_mode:
            text = self._strip_json_markdown(content)
            return json.loads(text)
        return content
