"""
system/__init__.py

NEO AI OS - System Module Manager

Responsibilities:
- Initialize and manage core system components
- Integrate SystemMonitor, ProcessManager, Scheduler
- Handle lifecycle (start/stop)
- Track system metrics (processes, tasks, errors)
- EventBus integration

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event
from system.system_monitor import GlobalSystemMonitor
from system.process_manager import GlobalProcessManager
from system.scheduler import GlobalScheduler


class SystemError(Exception):
    pass


class SystemManager:
    def __init__(self):
        self.event_bus = GlobalEventBus

        self.monitor = GlobalSystemMonitor
        self.process = GlobalProcessManager
        self.scheduler = GlobalScheduler

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.process_events: int = 0
        self.scheduled_tasks: int = 0
        self.errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.System.Manager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [System.Manager] %(message)s"
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

                self.logger.info("System Manager started")
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
                self.logger.info("System Manager stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics
    # =========================

    def _inc_process(self):
        with self._lock:
            self.process_events += 1

    def _inc_task(self):
        with self._lock:
            self.scheduled_tasks += 1

    def _inc_error(self):
        with self._lock:
            self.errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            return {
                "status": "running" if self._running else "stopped",
                "uptime": round(uptime, 2),
                "process_events": self.process_events,
                "scheduled_tasks": self.scheduled_tasks,
                "errors": self.errors,
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("system.process.*", self._on_process, priority=7)
            self.event_bus.subscribe("system.task.scheduled", self._on_task, priority=8)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_process(self, event: Event):
        try:
            self._inc_process()
        except Exception as e:
            self._error("process_event", e)

    def _on_task(self, event: Event):
        try:
            self._inc_task()
        except Exception as e:
            self._error("task_event", e)

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
                "system.error.system_manager",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalSystemManager = SystemManager()