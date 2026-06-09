"""AST-based Python syntax checking."""
from __future__ import annotations

import ast
from typing import Any, Dict, List


class SyntaxCheckResult:
    def __init__(self, valid: bool, errors: List[Dict[str, Any]]):
        self.valid = valid
        self.errors = errors


def check_syntax(code: str) -> SyntaxCheckResult:
    errors: List[Dict[str, Any]] = []
    try:
        ast.parse(code)
        return SyntaxCheckResult(valid=True, errors=errors)
    except SyntaxError as exc:
        errors.append(
            {
                "message": exc.msg or "Syntax error",
                "line": exc.lineno or 1,
                "offset": exc.offset or 0,
                "text": exc.text or "",
            }
        )
    except Exception as exc:
        errors.append({"message": str(exc), "line": 1, "offset": 0, "text": ""})
    return SyntaxCheckResult(valid=False, errors=errors)
