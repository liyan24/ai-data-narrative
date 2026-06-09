"""Discover and track files produced by code execution."""
from __future__ import annotations

from pathlib import Path
from typing import List, Set


OUTPUT_EXTENSIONS: Set[str] = {".png", ".csv", ".json", ".html", ".md", ".pdf", ".xlsx"}


def discover_outputs(directory: str | Path, since_mtime: float | None = None) -> List[str]:
    """Return absolute paths of output files under directory."""
    root = Path(directory)
    if not root.exists():
        return []
    files = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in OUTPUT_EXTENSIONS:
            if since_mtime is None or path.stat().st_mtime >= since_mtime:
                files.append(str(path.resolve()))
    return sorted(files)


def register_output(path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p.resolve())
