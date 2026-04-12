"""
ui/__init__.py

NEO AI OS - UI Module Manager

Responsibilities:
- Initialize and manage UI subsystems
- Integrate DesktopOverlay and NotificationManager
- Handle lifecycle (start/stop)
- Track UI metrics (notifications, renders, errors)
- EventBus integration

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event
from ui.desktop_overlay import GlobalDesktopOverlay
from ui.notification_manager import GlobalNotificationManager


class UIError(Exception):
    pass


class UIManager:
    def __init__(self):
        self.event_bus = GlobalEventBus

        self.overlay = GlobalDesktopOverlay
        self.notifications = GlobalNotificationManager

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.notifications_sent: int = 0
        self.overlay_updates: int = 0
        self.errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.UI.Manager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [UI.Manager] %(message)s"
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

                self.overlay.start()
                self.notifications.start()

                self.start_time = time.time()
                self._running = True

                self.logger.info("UI Manager started")
                return True

            except Exception as e:
                self._error("start", e)
                return False

    def stop(self) -> bool:
        with self._lock:
            try:
                if not self._running:
                    return False

                self.notifications.stop()

                self._running = False
                self.logger.info("UI Manager stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics
    # =========================

    def _inc_notification(self):
        with self._lock:
            self.notifications_sent += 1

    def _inc_overlay(self):
        with self._lock:
            self.overlay_updates += 1

    def _inc_error(self):
        with self._lock:
            self.errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            return {
                "status": "running" if self._running else "stopped",
                "uptime": round(uptime, 2),
                "notifications_sent": self.notifications_sent,
                "overlay_updates": self.overlay_updates,
                "errors": self.errors,
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("ui.notify", self._on_notify, priority=9)
            self.event_bus.subscribe("ui.overlay.update", self._on_overlay, priority=8)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_notify(self, event: Event):
        try:
            self._inc_notification()
        except Exception as e:
            self._error("notify_event", e)

    def _on_overlay(self, event: Event):
        try:
            self._inc_overlay()
        except Exception as e:
            self._error("overlay_event", e)

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
                "system.error.ui_manager",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalUIManager = UIManager()