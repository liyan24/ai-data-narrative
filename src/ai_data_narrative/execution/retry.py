"""Retry logic with optional LLM-driven code repair."""
from __future__ import annotations

import random
import time
from typing import Any, Callable, Dict, Optional

from ai_data_narrative.interfaces import BaseLLMProvider


class RetryPolicy:
    def __init__(
        self,
        max_retries: int = 2,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential = exponential

    def sleep(self, attempt: int) -> None:
        delay = min(
            self.base_delay * (2 ** attempt) if self.exponential else self.base_delay,
            self.max_delay,
        )
        delay *= random.uniform(0.8, 1.2)
        time.sleep(delay)


def with_retry(
    fn: Callable[[], Any],
    policy: RetryPolicy,
    on_error: Optional[Callable[[Exception, int], None]] = None,
) -> Any:
    last_exc: Optional[Exception] = None
    for attempt in range(policy.max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if on_error:
                on_error(exc, attempt)
            if attempt < policy.max_retries:
                policy.sleep(attempt)
    raise last_exc or RuntimeError("Retry exhausted")


def repair_code_with_llm(
    llm: BaseLLMProvider,
    original_code: str,
    error_message: str,
    task_description: str = "",
) -> str:
    system = "You are a coding assistant. Fix the provided Python code based on the error message. Return only the corrected code inside a Markdown python block."
    prompt = f"""Task: {task_description or 'Fix the following Python code'}

Original code:
```python
{original_code}
```

Error:
{error_message}

Please return the corrected Python code in a single Markdown code block.
"""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    result = llm.complete(messages, json_mode=False)
    text = result if isinstance(result, str) else str(result)
    # Extract code block
    if "```python" in text:
        text = text.split("```python", 1)[1]
    elif "```" in text:
        text = text.split("```", 1)[1]
    if "```" in text:
        text = text.split("```", 1)[0]
    return text.strip()
