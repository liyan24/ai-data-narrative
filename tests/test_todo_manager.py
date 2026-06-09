"""Tests for TodoManager."""
import pytest

from ai_data_narrative.models import Priority, TaskStatus
from ai_data_narrative.workflow.todo_manager import TodoManager


def test_add_and_get_task():
    tm = TodoManager()
    tm.add_task("t1", "Task One", priority=Priority.HIGH)
    task = tm.get_task("t1")
    assert task is not None
    assert task.status == TaskStatus.PENDING


def test_dependency_blocks_start():
    tm = TodoManager()
    tm.add_task("t1", "First")
    tm.add_task("t2", "Second", dependencies=["t1"])
    with pytest.raises(ValueError):
        tm.start_task("t2")


def test_lifecycle():
    tm = TodoManager()
    tm.add_task("t1", "First")
    tm.start_task("t1")
    tm.complete_task("t1", artifacts={"result": 42})
    assert tm.get_task("t1").status == TaskStatus.COMPLETED
    assert tm.get_task("t1").artifacts["result"] == 42


def test_progress():
    tm = TodoManager()
    tm.add_task("t1", "A")
    tm.add_task("t2", "B")
    tm.start_task("t1")
    tm.complete_task("t1")
    prog = tm.get_progress()
    assert prog.total == 2
    assert prog.completed == 1
    assert prog.percent == 50.0


def test_ready_tasks_order():
    tm = TodoManager()
    tm.add_task("t1", "Low", priority=Priority.LOW)
    tm.add_task("t2", "High", priority=Priority.HIGH)
    ready = tm.get_ready_tasks()
    assert ready[0].id == "t2"


def test_retry():
    tm = TodoManager()
    tm.add_task("t1", "A")
    tm.start_task("t1")
    tm.fail_task("t1", "boom")
    tm.retry_task("t1")
    assert tm.get_task("t1").status == TaskStatus.PENDING
    assert tm.get_task("t1").error is None


def test_save_load(tmp_path):
    tm = TodoManager()
    tm.add_task("t1", "A")
    tm.start_task("t1")
    tm.complete_task("t1", artifacts={"x": 1})
    path = tmp_path / "todo.json"
    tm.save(str(path))

    tm2 = TodoManager()
    tm2.load(str(path))
    assert tm2.get_task("t1").status == TaskStatus.COMPLETED
    assert tm2.get_task("t1").artifacts["x"] == 1
