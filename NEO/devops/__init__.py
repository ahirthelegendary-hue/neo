"""
devops/__init__.py

NEO AI OS - DevOps Module Initializer

Responsibilities:
- Initialize and manage DevOps subsystems
- Provide unified interface for CodeAnalyzer and GitManager
- Handle lifecycle (start/stop)
- Integrate with EventBus
- Track DevOps metrics (analysis, commits, errors)

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event
from devops.code_analyzer import GlobalCodeAnalyzer
from devops.git_manager import GlobalGitManager


class DevOpsError(Exception):
    """DevOps exception"""
    pass


class DevOpsManager:
    """
    Central DevOps manager.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus

        self.code_analyzer = GlobalCodeAnalyzer
        self.git = GlobalGitManager

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.analysis_runs: int = 0
        self.git_operations: int = 0
        self.errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.DevOps.Manager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [DevOps.Manager] %(message)s"
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

                self.logger.info("DevOps Manager started")
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
                self.logger.info("DevOps Manager stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics
    # =========================

    def _inc_analysis(self):
        with self._lock:
            self.analysis_runs += 1

    def _inc_git(self):
        with self._lock:
            self.git_operations += 1

    def _inc_error(self):
        with self._lock:
            self.errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            return {
                "status": "running" if self._running else "stopped",
                "uptime": round(uptime, 2),
                "analysis_runs": self.analysis_runs,
                "git_operations": self.git_operations,
                "errors": self.errors,
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("devops.analyze.result", self._on_analysis, priority=8)
            self.event_bus.subscribe("devops.git.*", self._on_git, priority=7)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_analysis(self, event: Event):
        try:
            self._inc_analysis()
        except Exception as e:
            self._error("analysis_event", e)

    def _on_git(self, event: Event):
        try:
            self._inc_git()
        except Exception as e:
            self._error("git_event", e)

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
                "system.error.devops_manager",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalDevOpsManager = DevOpsManager()