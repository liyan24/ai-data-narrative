"""Anthropic API provider."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ai_data_narrative.config import ANTHROPIC_API_KEY
from ai_data_narrative.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    name: str = "anthropic"
    weight: float = 1.0

    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20240620"):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key or ANTHROPIC_API_KEY)
        self.model = model

    def complete(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> str | Dict[str, Any]:
        system = ""
        chat_messages = messages
        if messages and messages[0].get("role") == "system":
            system = messages[0].get("content", "")
            chat_messages = messages[1:]
        if json_mode and system:
            system += "\nYou must respond with valid JSON only."
        elif json_mode:
            system = "You must respond with valid JSON only."

        resp = self.client.messages.create(
            model=self.model,
            system=system,
            messages=chat_messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        content = ""
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                content += block.text
        if json_mode:
            text = self._strip_json_markdown(content)
            return json.loads(text)
        return content
