"""
ui/notification_manager.py

NEO AI OS - Notification Manager

Responsibilities:
- Centralized notification handling system
- Display system alerts, AI responses, and warnings
- Manage notification queue and priority
- Support multiple notification channels (UI, sound, logs)
- Integrate with EventBus

Features:
- Priority-based notification queue
- Auto-dismiss timers
- Sound alerts (optional)
- Event-driven notifications
- Thread-safe queue management
- Async + Sync support

"""

from __future__ import annotations

import threading
import logging
import traceback
import asyncio
import time
from typing import Dict, Any, List

from core.event_bus import GlobalEventBus, Event


class NotificationError(Exception):
    """Notification exception"""


class Notification:
    def __init__(
        self,
        message: str,
        level: str = "info",
        priority: int = 5,
        duration: int = 3,
    ):
        self.message = message
        self.level = level
        self.priority = priority
        self.duration = duration
        self.timestamp = time.time()


class NotificationManager:
    """
    Manages all notifications across NEO.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.queue: List[Notification] = []
        self.running = False

        self.logger = logging.getLogger("NEO.Notification")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Notification] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("notify", self._on_notify, priority=9)
        self.event_bus.subscribe("system.error.*", self._on_error, priority=10)
        self.event_bus.subscribe("ai.*", self._on_ai_event, priority=5)

    # =========================
    # Notification Handling
    # =========================

    def push(self, notification: Notification):
        with self._lock:
            self.queue.append(notification)
            self.queue.sort(key=lambda n: n.priority, reverse=True)

            self.logger.info(f"Notification: {notification.message}")

    def _dispatch(self, notification: Notification):
        try:
            # Emit to UI
            self.event_bus.publish(
                "ui.notify",
                {"message": notification.message},
                priority=notification.priority,
            )

        except Exception as e:
            self._error("dispatch", e)

    # =========================
    # Processing Loop
    # =========================

    def _loop(self):
        while self.running:
            try:
                if self.queue:
                    with self._lock:
                        notification = self.queue.pop(0)

                    self._dispatch(notification)

                    time.sleep(notification.duration)

                else:
                    time.sleep(0.5)

            except Exception as e:
                self._error("loop", e)

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self._loop, daemon=True).start()
            self.logger.info("Notification system started")

    def stop(self):
        self.running = False
        self.logger.info("Notification system stopped")

    # =========================
    # Event Handlers
    # =========================

    def _on_notify(self, event: Event):
        try:
            msg = event.data.get("message", "Notification")
            level = event.data.get("level", "info")

            self.push(Notification(msg, level=level))

        except Exception as e:
            self._error("event_notify", e)

    def _on_error(self, event: Event):
        try:
            msg = f"ERROR: {event.data.get('error')}"
            self.push(Notification(msg, level="error", priority=10))
        except Exception as e:
            self._error("event_error", e)

    def _on_ai_event(self, event: Event):
        try:
            msg = f"AI Event: {event.name}"
            self.push(Notification(msg, level="info", priority=4))
        except Exception as e:
            self._error("event_ai", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.notification",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def push_async(self, notification: Notification):
        return await asyncio.to_thread(self.push, notification)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalNotificationManager = NotificationManager()