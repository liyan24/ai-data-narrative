"""OpenAI API provider."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from ai_data_narrative.config import OPENAI_API_KEY
from ai_data_narrative.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    name: str = "openai"
    weight: float = 1.0

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini", base_url: str | None = None):
        from openai import OpenAI

        self.client = OpenAI(
            api_key=api_key or OPENAI_API_KEY,
            base_url=base_url or None,
        )
        self.model = model

    def complete(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> str | Dict[str, Any]:
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            response_format=response_format,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        content = resp.choices[0].message.content or ""
        if json_mode:
            text = self._strip_json_markdown(content)
            return json.loads(text)
        return content
