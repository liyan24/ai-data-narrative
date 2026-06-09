"""Base LLM provider interface."""
from __future__ import annotations

from typing import Any, Dict, List

from ai_data_narrative.interfaces import BaseLLMProvider


class LLMProvider(BaseLLMProvider):
    """Convenience base with helper methods."""

    name: str = "base"
    weight: float = 1.0

    def complete(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> str | Dict[str, Any]:
        raise NotImplementedError

    def _strip_json_markdown(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text
