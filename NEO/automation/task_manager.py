"""
automation/task_manager.py

NEO AI OS - Task Automation Manager

Responsibilities:
- Manage user-defined automation tasks
- Trigger tasks based on events, time, or conditions
- Chain multiple actions into workflows
- Integrate with EventBus for system-wide automation
- Maintain task history and execution logs

Features:
- Event-based triggers
- Conditional execution
- Workflow chaining
- Retry + failure handling
- Thread-safe
- Async + Sync support
- Persistent-ready structure

"""

from __future__ import annotations

import threading
import logging
import traceback
import asyncio
import time
from typing import Dict, Any, Callable, List, Optional

from core.event_bus import GlobalEventBus, Event


class TaskManagerError(Exception):
    """Task manager exception"""


class Task:
    def __init__(
        self,
        name: str,
        trigger: str,
        actions: List[Dict[str, Any]],
        condition: Optional[Callable[[], bool]] = None,
        retries: int = 0,
        cooldown: int = 0,
    ):
        self.name = name
        self.trigger = trigger
        self.actions = actions
        self.condition = condition
        self.retries = retries
        self.cooldown = cooldown

        self.last_run: float = 0
        self.failed_attempts: int = 0


class TaskManager:
    """
    Automation engine for chaining tasks.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.tasks: Dict[str, Task] = {}
        self.history: List[Dict[str, Any]] = []

        self.logger = logging.getLogger("NEO.TaskManager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [TaskManager] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("*", self._on_event, priority=1)

    # =========================
    # Task Management
    # =========================

    def add_task(self, task: Task):
        with self._lock:
            self.tasks[task.name] = task
            self.logger.info(f"Task added: {task.name}")

    def remove_task(self, name: str):
        with self._lock:
            if name in self.tasks:
                del self.tasks[name]
                self.logger.info(f"Task removed: {name}")

    def list_tasks(self) -> List[str]:
        return list(self.tasks.keys())

    # =========================
    # Event Listener
    # =========================

    def _on_event(self, event: Event):
        """
        Listen to ALL events and trigger tasks.
        """
        try:
            for task in list(self.tasks.values()):
                if task.trigger == event.name:
                    self._execute_task(task, event)

        except Exception as e:
            self._error("on_event", e)

    # =========================
    # Execution Logic
    # =========================

    def _execute_task(self, task: Task, event: Event):
        with self._lock:
            now = time.time()

            if now - task.last_run < task.cooldown:
                return

            if task.condition and not task.condition():
                return

            self.logger.info(f"Executing task: {task.name}")

            success = True

            for action in task.actions:
                try:
                    self.event_bus.publish(
                        action["type"],
                        action.get("payload", {}),
                        priority=action.get("priority", 5),
                    )
                except Exception as e:
                    success = False
                    self.logger.error(f"Action failed: {e}")

            task.last_run = now

            if not success:
                task.failed_attempts += 1
                if task.failed_attempts <= task.retries:
                    self.logger.warning(f"Retrying task: {task.name}")
                    self._execute_task(task, event)
            else:
                task.failed_attempts = 0

            # Save history
            self.history.append({
                "task": task.name,
                "event": event.name,
                "success": success,
                "timestamp": now,
            })

            # Emit result
            self.event_bus.publish(
                "automation.task.completed",
                {
                    "task": task.name,
                    "success": success,
                },
                priority=7,
            )

    # =========================
    # History
    # =========================

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history[-100:]  # last 100

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.task_manager",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def add_task_async(self, task: Task):
        return await asyncio.to_thread(self.add_task, task)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalTaskManager = TaskManager()