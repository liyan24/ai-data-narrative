"""Sandboxed execution of Python code with restricted globals and timeout."""
from __future__ import annotations

import signal
import sys
import threading
import traceback
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any, Dict, List, Optional

from ai_data_narrative.config import SAFE_BUILTINS
from ai_data_narrative.execution.security_scanner import scan_code
from ai_data_narrative.models import SkillOutput


class Sandbox:
    """Execute Python code in a restricted namespace."""

    def __init__(
        self,
        timeout: int = 120,
        allowed_builtins: Optional[set] = None,
        inject: Optional[Dict[str, Any]] = None,
    ):
        self.timeout = timeout
        self.allowed_builtins = allowed_builtins or SAFE_BUILTINS
        self.inject = inject or {}

    def run(self, code: str) -> SkillOutput:
        # Pre-flight security scan
        scan = scan_code(code)
        if not scan.safe:
            messages = [f"{i.line}: {i.message}" for i in scan.issues]
            return SkillOutput(
                skill_name="sandbox",
                success=False,
                stderr="Security violation:\n" + "\n".join(messages),
                error="security_scan_failed",
            )

        stdout_capture = StringIO()
        stderr_capture = StringIO()
        return_value: Any = None
        exception: Optional[Exception] = None

        safe_globals = {
            "__builtins__": {name: __builtins__[name] for name in self.allowed_builtins if name in __builtins__},  # type: ignore[index]
        }
        safe_globals.update(self.inject)
        safe_locals: Dict[str, Any] = {}

        def target() -> None:
            nonlocal return_value, exception
            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(code, safe_globals, safe_locals)
                # If the code defines a `result` variable, capture it
                return_value = safe_locals.get("result")
            except Exception as exc:
                exception = exc

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            # We cannot safely kill a thread in pure Python; mark as timeout
            return SkillOutput(
                skill_name="sandbox",
                success=False,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue() + f"\nTimeout after {self.timeout}s",
                error="timeout",
            )

        if exception is not None:
            tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
            return SkillOutput(
                skill_name="sandbox",
                success=False,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue() + "\n" + "".join(tb),
                error=str(exception),
            )

        return SkillOutput(
            skill_name="sandbox",
            success=True,
            stdout=stdout_capture.getvalue(),
            stderr=stderr_capture.getvalue(),
            return_value=return_value,
        )
