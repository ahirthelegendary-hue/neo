"""
plugins/base_plugin.py

FIXED VERSION (GlobalEventBus type issue resolved)
"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any, Callable, List

from core.event_bus import GlobalEventBus, Event


class PluginBaseError(Exception):
    pass


class BasePlugin:
    def __init__(self, name: str):
        self.name = name
        self.event_bus = GlobalEventBus

        self._lock = threading.RLock()
        self._enabled = False
        self._loaded = False
        self._subscriptions: List[Dict[str, Any]] = []

        self.start_time: float = 0.0
        self.events_handled: int = 0
        self.errors: int = 0

        self.logger = logging.getLogger(f"NEO.Plugin.{self.name}")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"[%(asctime)s] [%(levelname)s] [Plugin:{self.name}] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    # =========================
    # Lifecycle
    # =========================

    def on_load(self, event_bus):
        """
        FIX: Removed wrong type hint (GlobalEventBus)
        """
        with self._lock:
            try:
                self._loaded = True
                self._enabled = True
                self.start_time = time.time()
                self.logger.info("Plugin loaded")
            except Exception as e:
                self._error("on_load", e)

    def on_unload(self):
        with self._lock:
            try:
                self._subscriptions.clear()
                self._loaded = False
                self._enabled = False
                self.logger.info("Plugin unloaded")
            except Exception as e:
                self._error("on_unload", e)

    def enable(self):
        with self._lock:
            self._enabled = True
            self.logger.info("Plugin enabled")

    def disable(self):
        with self._lock:
            self._enabled = False
            self.logger.info("Plugin disabled")

    def is_enabled(self) -> bool:
        return self._enabled

    def is_loaded(self) -> bool:
        return self._loaded

    # =========================
    # Event Subscription
    # =========================

    def subscribe(self, event_name: str, handler: Callable, priority: int = 5):
        try:
            wrapped = self._wrap_handler(handler)
            self.event_bus.subscribe(event_name, wrapped, priority=priority)

            self._subscriptions.append({
                "event": event_name,
                "handler": wrapped,
            })

        except Exception as e:
            self._error("subscribe", e)

    def _wrap_handler(self, handler: Callable):
        def safe_handler(event: Event):
            try:
                if not self._enabled:
                    return

                handler(event)

                with self._lock:
                    self.events_handled += 1

            except Exception as e:
                self._error("handler", e)

        return safe_handler

    # =========================
    # Metrics
    # =========================

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._loaded else 0

            return {
                "name": self.name,
                "enabled": self._enabled,
                "loaded": self._loaded,
                "uptime": round(uptime, 2),
                "events_handled": self.events_handled,
                "errors": self.errors,
            }

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        with self._lock:
            self.errors += 1

        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.plugin_base",
                {
                    "plugin": self.name,
                    "source": source,
                    "error": str(error),
                },
                priority=10,
            )
        except Exception:
            pass