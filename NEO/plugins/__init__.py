"""
plugins/__init__.py

NEO AI OS - Plugin System Initializer & Manager

Responsibilities:
- Centralized plugin lifecycle management
- Load/Unload/Enable/Disable plugins
- Integrate plugins with EventBus
- Maintain plugin registry & metrics
- Handle system-wide plugin hooks

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any, List

from core.event_bus import GlobalEventBus, Event
from plugins.plugin_manager import GlobalPluginManager


class PluginSystemError(Exception):
    """Plugin system exception"""
    pass


class PluginSystem:
    """
    Advanced Plugin System Manager.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self.manager = GlobalPluginManager

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.loaded_plugins: int = 0
        self.enabled_plugins: int = 0
        self.errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.PluginSystem")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [PluginSystem] %(message)s"
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

                self.manager.discover()

                self.start_time = time.time()
                self._running = True

                self._update_metrics()

                self.logger.info("Plugin system started")
                return True

            except Exception as e:
                self._error("start", e)
                return False

    def stop(self) -> bool:
        with self._lock:
            try:
                if not self._running:
                    return False

                for name in list(self.manager.plugins.keys()):
                    self.manager.unload_plugin(name)

                self._running = False

                self.logger.info("Plugin system stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics
    # =========================

    def _update_metrics(self):
        with self._lock:
            self.loaded_plugins = len(self.manager.plugins)
            self.enabled_plugins = sum(1 for v in self.manager.enabled.values() if v)

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            self._update_metrics()

            return {
                "status": "running" if self._running else "stopped",
                "uptime": round(uptime, 2),
                "loaded_plugins": self.loaded_plugins,
                "enabled_plugins": self.enabled_plugins,
                "errors": self.errors,
            }

    def list_plugins(self) -> List[str]:
        return self.manager.list_plugins()

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("plugins.reload", self._on_reload, priority=9)
            self.event_bus.subscribe("plugins.disable", self._on_disable, priority=9)
            self.event_bus.subscribe("plugins.enable", self._on_enable, priority=9)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_reload(self, event: Event):
        try:
            self.manager.discover()
            self._update_metrics()
        except Exception as e:
            self._error("reload", e)

    def _on_disable(self, event: Event):
        try:
            name = event.data.get("name")
            self.manager.disable_plugin(name)
            self._update_metrics()
        except Exception as e:
            self._error("disable", e)

    def _on_enable(self, event: Event):
        try:
            name = event.data.get("name")
            self.manager.enable_plugin(name)
            self._update_metrics()
        except Exception as e:
            self._error("enable", e)

    def _on_shutdown(self, event: Event):
        try:
            self.stop()
        except Exception as e:
            self._error("shutdown", e)

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
                "system.error.plugins",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalPluginSystem = PluginSystem()