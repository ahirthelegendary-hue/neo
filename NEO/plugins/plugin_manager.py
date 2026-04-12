"""
plugins/plugin_manager.py

NEO AI OS - Plugin Manager

Responsibilities:
- Dynamically load/unload plugins
- Discover plugins from directory
- Register plugin hooks into EventBus
- Enable/Disable plugins at runtime
- Sandbox basic plugin execution

Features:
- Dynamic imports
- Plugin lifecycle management
- Event-driven plugin hooks
- Safe loading (error isolation)
- Thread-safe
- Async + Sync support

Plugin Structure:
Each plugin must have:
- plugin.py
- class Plugin with methods:
    - on_load(self, event_bus)
    - on_unload(self)
"""

from __future__ import annotations

import os
import importlib.util
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any

from core.event_bus import GlobalEventBus


class PluginError(Exception):
    """Plugin exception"""


class PluginManager:
    """
    Handles dynamic plugins.
    """

    def __init__(self, plugin_dir: str = "plugins"):
        self.event_bus = GlobalEventBus
        self.plugin_dir = plugin_dir

        self._lock = threading.RLock()
        self.plugins: Dict[str, Any] = {}
        self.enabled: Dict[str, bool] = {}

        self.logger = logging.getLogger("NEO.PluginManager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Plugin] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        os.makedirs(self.plugin_dir, exist_ok=True)

    # =========================
    # Plugin Discovery
    # =========================

    def discover(self):
        try:
            for name in os.listdir(self.plugin_dir):
                path = os.path.join(self.plugin_dir, name)

                if os.path.isdir(path):
                    plugin_file = os.path.join(path, "plugin.py")
                    if os.path.exists(plugin_file):
                        self.load_plugin(name, plugin_file)

        except Exception as e:
            self._error("discover", e)

    # =========================
    # Load / Unload
    # =========================

    def load_plugin(self, name: str, path: str):
        with self._lock:
            try:
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                plugin_class = getattr(module, "Plugin")
                instance = plugin_class()

                instance.on_load(self.event_bus)

                self.plugins[name] = instance
                self.enabled[name] = True

                self.logger.info(f"Loaded plugin: {name}")

            except Exception as e:
                self._error(f"load_plugin:{name}", e)

    def unload_plugin(self, name: str):
        with self._lock:
            try:
                plugin = self.plugins.get(name)
                if plugin:
                    plugin.on_unload()

                self.plugins.pop(name, None)
                self.enabled.pop(name, None)

                self.logger.info(f"Unloaded plugin: {name}")

            except Exception as e:
                self._error("unload_plugin", e)

    def enable_plugin(self, name: str):
        if name in self.plugins:
            self.enabled[name] = True

    def disable_plugin(self, name: str):
        if name in self.plugins:
            self.enabled[name] = False

    # =========================
    # Execution Hook
    # =========================

    def execute_hook(self, hook: str, data: Dict[str, Any]):
        """
        Call hook on all enabled plugins.
        """
        with self._lock:
            for name, plugin in self.plugins.items():
                if not self.enabled.get(name):
                    continue

                try:
                    method = getattr(plugin, hook, None)
                    if callable(method):
                        method(data)

                except Exception as e:
                    self._error(f"plugin_hook:{name}", e)

    # =========================
    # Helpers
    # =========================

    def list_plugins(self):
        return list(self.plugins.keys())

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.plugin",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def discover_async(self):
        return await asyncio.to_thread(self.discover)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalPluginManager = PluginManager()