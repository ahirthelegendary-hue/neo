"""
ui/widgets.py

NEO AI OS - UI Widgets System

Responsibilities:
- Provide reusable UI widgets
- Manage widget lifecycle and rendering
- Support dynamic updates via EventBus
- Track widget metrics

Features:
- Thread-safe widget registry
- BaseWidget class for extension
- Live update support
- Metrics tracking
"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any, Callable

from core.event_bus import GlobalEventBus, Event


class WidgetError(Exception):
    pass


class BaseWidget:
    """
    Base class for all UI widgets.
    """

    def __init__(self, name: str):
        self.name = name
        self._lock = threading.RLock()
        self.data: Dict[str, Any] = {}
        self.last_updated: float = 0.0
        self.render_count: int = 0
        self.errors: int = 0

        self.logger = logging.getLogger(f"NEO.Widget.{self.name}")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"[%(asctime)s] [%(levelname)s] [Widget:{self.name}] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def update(self, data: Dict[str, Any]):
        with self._lock:
            try:
                self.data = data
                self.last_updated = time.time()
            except Exception as e:
                self._error("update", e)

    def render(self) -> str:
        with self._lock:
            try:
                self.render_count += 1
                return f"{self.name}: {self.data}"
            except Exception as e:
                self._error("render", e)
                return f"{self.name}: error"

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "last_updated": self.last_updated,
            "render_count": self.render_count,
            "errors": self.errors,
        }

    def _error(self, source: str, error: Exception):
        self.errors += 1
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())


class WidgetManager:
    """
    Manages all UI widgets.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus

        self._lock = threading.RLock()
        self.widgets: Dict[str, BaseWidget] = {}

        self.logger = logging.getLogger("NEO.WidgetManager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [WidgetManager] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._subscribe_events()

    # =========================
    # Widget Management
    # =========================

    def register(self, widget: BaseWidget):
        with self._lock:
            self.widgets[widget.name] = widget
            self.logger.info(f"Widget registered: {widget.name}")

    def unregister(self, name: str):
        with self._lock:
            if name in self.widgets:
                del self.widgets[name]
                self.logger.info(f"Widget removed: {name}")

    def get(self, name: str) -> BaseWidget | None:
        return self.widgets.get(name)

    def render_all(self) -> Dict[str, str]:
        output = {}
        with self._lock:
            for name, widget in self.widgets.items():
                output[name] = widget.render()
        return output

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                name: widget.get_metrics()
                for name, widget in self.widgets.items()
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("ui.widget.update", self._on_update, priority=8)
        except Exception as e:
            self._error("subscribe", e)

    def _on_update(self, event: Event):
        try:
            name = event.data.get("name")
            data = event.data.get("data", {})

            widget = self.get(name)
            if widget:
                widget.update(data)

        except Exception as e:
            self._error("update_event", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.widgets",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalWidgetManager = WidgetManager()