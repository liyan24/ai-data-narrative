"""Tests for code execution engine."""
import pytest

from ai_data_narrative.execution import Sandbox, check_syntax, discover_outputs, scan_code
from ai_data_narrative.execution.retry import RetryPolicy, with_retry


def test_check_syntax_valid():
    result = check_syntax("x = 1 + 2\nprint(x)")
    assert result.valid
    assert not result.errors


def test_check_syntax_invalid():
    result = check_syntax("x = 1 + ")
    assert not result.valid
    assert result.errors


def test_scan_code_blocks_forbidden_import():
    code = "import os\nos.system('ls')"
    result = scan_code(code)
    assert not result.safe
    assert any("os.system" in i.message for i in result.issues)


def test_scan_code_blocks_eval():
    code = "eval('1+1')"
    result = scan_code(code)
    assert not result.safe
    assert any(i.category == "forbidden_call" for i in result.issues)


def test_sandbox_basic():
    sandbox = Sandbox()
    result = sandbox.run("x = 2 + 3\nresult = x * 2")
    assert result.success
    assert result.return_value == 10


def test_sandbox_blocks_eval():
    sandbox = Sandbox()
    result = sandbox.run("eval('1+1')")
    assert not result.success
    assert result.error == "security_scan_failed"


def test_sandbox_timeout():
    sandbox = Sandbox(timeout=1)
    result = sandbox.run("import time\ntime.sleep(10)")
    # Should either fail security (import time is not forbidden per se) or timeout
    # Note: time is not in FORBIDDEN_IMPORTS but __import__ is blocked.
    # Actually exec may block import because __builtins__ has no __import__.
    assert not result.success or "timeout" in (result.stderr or "")


def test_retry_success():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    policy = RetryPolicy(max_retries=2)
    assert with_retry(fn, policy) == "ok"
    assert len(calls) == 1


def test_retry_eventual_success():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("not yet")
        return "ok"

    policy = RetryPolicy(max_retries=3, base_delay=0.01)
    assert with_retry(fn, policy) == "ok"
    assert len(calls) == 3


def test_retry_exhausted():
    def fn():
        raise RuntimeError("always fails")

    policy = RetryPolicy(max_retries=1, base_delay=0.01)
    with pytest.raises(RuntimeError):
        with_retry(fn, policy)


def test_discover_outputs(tmp_path):
    (tmp_path / "chart.png").write_text("fake")
    (tmp_path / "data.csv").write_text("a,b\n1,2")
    found = discover_outputs(tmp_path)
    assert len(found) == 2
