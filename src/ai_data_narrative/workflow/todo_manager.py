"""Task lifecycle, dependency tracking, and progress reporting."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai_data_narrative.models import Priority, Progress, Task, TaskStatus


class TodoManager:
    """Manages a DAG of tasks with lifecycle transitions."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def add_task(
        self,
        task_id: str,
        name: str,
        description: str = "",
        agent: str = "",
        priority: Priority = Priority.HIGH,
        dependencies: Optional[List[str]] = None,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> Task:
        if task_id in self._tasks:
            raise ValueError(f"Task {task_id} already exists")
        task = Task(
            id=task_id,
            name=name,
            description=description,
            agent=agent,
            priority=priority,
            dependencies=dependencies or [],
            artifacts=artifacts or {},
        )
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def start_task(self, task_id: str) -> Task:
        task = self._get_and_check(task_id, {TaskStatus.PENDING})
        if not self._dependencies_satisfied(task):
            deps = [d for d in task.dependencies if self._tasks.get(d) is None or self._tasks[d].status != TaskStatus.COMPLETED]
            raise ValueError(f"Dependencies not satisfied for {task_id}: {deps}")
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now(timezone.utc)
        return task

    def complete_task(self, task_id: str, artifacts: Optional[Dict[str, Any]] = None) -> Task:
        task = self._get_and_check(task_id, {TaskStatus.IN_PROGRESS})
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        if artifacts:
            task.artifacts.update(artifacts)
        return task

    def fail_task(self, task_id: str, error: str) -> Task:
        task = self._get_and_check(task_id, {TaskStatus.PENDING, TaskStatus.IN_PROGRESS})
        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = datetime.now(timezone.utc)
        return task

    def skip_task(self, task_id: str) -> Task:
        task = self._get_and_check(task_id, {TaskStatus.PENDING})
        task.status = TaskStatus.SKIPPED
        task.completed_at = datetime.now(timezone.utc)
        return task

    def retry_task(self, task_id: str) -> Task:
        task = self._get_and_check(task_id, {TaskStatus.FAILED, TaskStatus.SKIPPED})
        task.status = TaskStatus.PENDING
        task.error = None
        task.started_at = None
        task.completed_at = None
        return task

    def get_progress(self) -> Progress:
        total = len(self._tasks)
        counts = {
            TaskStatus.COMPLETED: 0,
            TaskStatus.FAILED: 0,
            TaskStatus.SKIPPED: 0,
            TaskStatus.IN_PROGRESS: 0,
            TaskStatus.PENDING: 0,
        }
        for t in self._tasks.values():
            counts[t.status] += 1
        percent = (counts[TaskStatus.COMPLETED] / total * 100) if total else 0.0
        return Progress(
            total=total,
            completed=counts[TaskStatus.COMPLETED],
            failed=counts[TaskStatus.FAILED],
            skipped=counts[TaskStatus.SKIPPED],
            in_progress=counts[TaskStatus.IN_PROGRESS],
            pending=counts[TaskStatus.PENDING],
            percent=round(percent, 2),
        )

    def get_ready_tasks(self) -> List[Task]:
        ready = []
        for task in self._tasks.values():
            if task.status == TaskStatus.PENDING and self._dependencies_satisfied(task):
                ready.append(task)
        # Higher priority first, then earlier created
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        ready.sort(key=lambda t: (priority_order.get(t.priority, 1), t.created_at))
        return ready

    def get_next_task(self) -> Optional[Task]:
        ready = self.get_ready_tasks()
        return ready[0] if ready else None

    def to_markdown(self) -> str:
        lines = ["# Task Board\n"]
        for task in self._tasks.values():
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.SKIPPED: "⏭️",
            }.get(task.status, "❓")
            lines.append(f"- {status_icon} **{task.name}** ({task.id}) — `{task.status.value}`")
            if task.error:
                lines.append(f"  - Error: {task.error}")
        lines.append(f"\n**Progress:** {self.get_progress().percent}%")
        return "\n".join(lines)

    def to_storyboard(self) -> str:
        lines = ["# Storyboard\n"]
        for task in self._tasks.values():
            lines.append(f"## {task.name}")
            lines.append(f"- Status: {task.status.value}")
            lines.append(f"- Agent: {task.agent or 'N/A'}")
            if task.artifacts.get("storyboard"):
                lines.append(f"- Storyboard: {task.artifacts['storyboard']}")
            lines.append("")
        return "\n".join(lines)

    def save(self, path: str) -> None:
        data = {tid: t.model_dump(mode="json") for tid, t in self._tasks.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._tasks = {tid: Task(**payload) for tid, payload in data.items()}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _get_and_check(self, task_id: str, allowed: set) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")
        if task.status not in allowed:
            raise ValueError(f"Invalid transition from {task.status.value} for {task_id}")
        return task

    def _dependencies_satisfied(self, task: Task) -> bool:
        for dep_id in task.dependencies:
            dep = self._tasks.get(dep_id)
            if dep is None or dep.status != TaskStatus.COMPLETED:
                return False
        return True
