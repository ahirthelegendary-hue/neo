"""
automation/__init__.py

NEO AI OS - Automation Module Initializer

Responsibilities:
- Initialize and manage automation subsystems
- Provide unified interface for TaskManager and WorkflowEngine
- Handle lifecycle (start/stop)
- Integrate with EventBus
- Track automation metrics

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event
from automation.task_manager import GlobalTaskManager
from automation.workflow_engine import GlobalWorkflowEngine


class AutomationError(Exception):
    """Automation exception"""
    pass


class AutomationManager:
    """
    Central automation manager.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus

        self.task_manager = GlobalTaskManager
        self.workflow_engine = GlobalWorkflowEngine

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.tasks_executed: int = 0
        self.workflows_executed: int = 0
        self.errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.Automation.Manager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Automation.Manager] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._subscribe_events()

    # =========================
    # Lifecycle
    # =========================

    def start(self) -> bool:
        with self._lock:
            try:
                if self._running:
                    return False

                self.start_time = time.time()
                self._running = True

                self.logger.info("Automation Manager started")
                return True

            except Exception as e:
                self._error("start", e)
                return False

    def stop(self) -> bool:
        with self._lock:
            try:
                if not self._running:
                    return False

                self._running = False
                self.logger.info("Automation Manager stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics
    # =========================

    def _inc_task(self):
        with self._lock:
            self.tasks_executed += 1

    def _inc_workflow(self):
        with self._lock:
            self.workflows_executed += 1

    def _inc_error(self):
        with self._lock:
            self.errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            return {
                "status": "running" if self._running else "stopped",
                "uptime": round(uptime, 2),
                "tasks_executed": self.tasks_executed,
                "workflows_executed": self.workflows_executed,
                "errors": self.errors,
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("automation.task.completed", self._on_task, priority=8)
            self.event_bus.subscribe("automation.workflow.completed", self._on_workflow, priority=8)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_task(self, event: Event):
        try:
            self._inc_task()
        except Exception as e:
            self._error("task_event", e)

    def _on_workflow(self, event: Event):
        try:
            self._inc_workflow()
        except Exception as e:
            self._error("workflow_event", e)

    def _on_shutdown(self, event: Event):
        try:
            self.stop()
        except Exception as e:
            self._error("shutdown_event", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self._inc_error()

        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.automation_manager",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalAutomationManager = AutomationManager()