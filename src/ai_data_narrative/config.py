"""Configuration and constants."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PASS_THRESHOLD = float(os.getenv("DEFAULT_PASS_THRESHOLD", "0.60"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

COLOR_PALETTE = {
    "primary": "#2E5C8A",
    "secondary": "#D9534F",
    "accent": "#FFD700",
    "background": "#FFFFFF",
    "text": "#333333",
}

GRADE_THRESHOLDS = [
    (0.95, "A+"),
    (0.90, "A"),
    (0.85, "A-"),
    (0.80, "B+"),
    (0.75, "B"),
    (0.70, "B-"),
    (0.65, "C+"),
    (0.60, "C"),
    (0.55, "C-"),
    (0.50, "D"),
]


def grade_from_score(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


FORBIDDEN_IMPORTS = {
    "os",
    "os.system",
    "subprocess",
    "eval",
    "exec",
    "socket",
    "urllib",
    "pickle",
    "ctypes",
    "compile",
    "importlib",
}

FORBIDDEN_BUILTINS = {"eval", "exec", "compile", "__import__", "open"}

SAFE_BUILTINS = {
    "__import__",
    "len",
    "range",
    "enumerate",
    "zip",
    "map",
    "filter",
    "sum",
    "min",
    "max",
    "abs",
    "round",
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "tuple",
    "set",
    "print",
    "sorted",
    "reversed",
    "hasattr",
    "getattr",
    "isinstance",
    "type",
    "dir",
}
