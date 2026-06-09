"""Extract Python code blocks from Markdown text."""
from __future__ import annotations

import re
from typing import List


def extract_python_code(text: str) -> List[str]:
    """Return all Python code blocks found in Markdown text."""
    pattern = re.compile(r"```python\s*(.*?)```", re.DOTALL | re.IGNORECASE)
    blocks = pattern.findall(text)
    return [block.strip() for block in blocks if block.strip()]


def first_python_code(text: str) -> str:
    """Return the first Python code block or empty string."""
    blocks = extract_python_code(text)
    return blocks[0] if blocks else ""


def extract_json_code(text: str) -> str:
    """Return the first JSON block content or the input stripped."""
    pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
    blocks = pattern.findall(text)
    if blocks:
        return blocks[0].strip()
    return text.strip()
