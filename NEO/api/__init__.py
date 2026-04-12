"""
api/__init__.py

NEO AI OS - Advanced API Manager

Production-grade API lifecycle manager responsible for:
- Starting/stopping API services
- EventBus integration
- Metrics & health tracking
- Thread-safe operations
- Broadcast handling

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any

from api.rest_server import GlobalRestServer
from core.event_bus import GlobalEventBus, Event


class APIManagerError(Exception):
    """API Manager exception"""
    pass


class APIManager:
    """
    Industrial-grade API Manager.

    Handles lifecycle, monitoring, and event integration for API layer.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self.server = GlobalRestServer

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.total_requests: int = 0
        self.total_errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.API.Manager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [API.Manager] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self._subscribe_events()

    # =========================
    # Lifecycle Management
    # =========================

    def start(self) -> bool:
        """
        Start API server safely.
        """
        with self._lock:
            try:
                if self._running:
                    self.logger.warning("API already running")
                    return False

                self.server.start()
                self.start_time = time.time()
                self._running = True

                self.logger.info("API Manager started")
                return True

            except Exception as e:
                self._error("start", e)
                return False

    def stop(self) -> bool:
        """
        Stop API server (graceful).
        """
        with self._lock:
            try:
                if not self._running:
                    return False

                # NOTE: uvicorn thread daemon -> stops with process
                self._running = False

                self.logger.info("API Manager stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics & Health
    # =========================

    def record_request(self):
        with self._lock:
            self.total_requests += 1

    def record_error(self):
        with self._lock:
            self.total_errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Return system metrics.
        """
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            return {
                "status": "running" if self._running else "stopped",
                "uptime_seconds": round(uptime, 2),
                "total_requests": self.total_requests,
                "total_errors": self.total_errors,
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
            self.event_bus.subscribe("api.broadcast", self._on_broadcast, priority=8)
            self.event_bus.subscribe("api.metrics.request", self._on_metrics_request, priority=9)

        except Exception as e:
            self._error("subscribe_events", e)

    def _on_shutdown(self, event: Event):
        """
        Handle system shutdown.
        """
        try:
            self.logger.info("Shutdown event received")
            self.stop()

        except Exception as e:
            self._error("shutdown_event", e)

    def _on_broadcast(self, event: Event):
        """
        Broadcast message to system (via EventBus).
        """
        try:
            message = event.data.get("message", "")

            self.logger.info(f"Broadcast: {message}")

            # Re-broadcast to UI or other systems
            self.event_bus.publish(
                "ui.notify",
                {"message": message},
                priority=7,
            )

        except Exception as e:
            self._error("broadcast", e)

    def _on_metrics_request(self, event: Event):
        """
        Respond with metrics.
        """
        try:
            metrics = self.get_metrics()

            self.event_bus.publish(
                "api.metrics.response",
                {"metrics": metrics},
                priority=9,
            )

        except Exception as e:
            self._error("metrics_request", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.total_errors += 1

        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.api_manager",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalAPIManager = APIManager()