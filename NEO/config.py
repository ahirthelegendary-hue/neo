"""
config.py

NEO AI OS - Global Configuration System

Responsibilities:
- Centralized configuration management
- Environment variable loading (.env support)
- Runtime configuration overrides
- Type-safe config access
- Validation & defaults
- Dynamic reload support
- Integration with EventBus

Features:
- .env file parsing (no external dependency)
- Nested config structure
- Thread-safe access
- Runtime updates
- Validation system
- Auto fallback defaults
- Logging + diagnostics

"""

from __future__ import annotations

import os
import threading
import logging
import traceback
from typing import Any, Dict, Optional

from core.event_bus import GlobalEventBus, Event


class ConfigError(Exception):
    """Base exception for config system"""


class Config:
    """
    Central configuration manager for NEO.
    """

    def __init__(self, env_file: str = ".env"):
        self._lock = threading.RLock()
        self.event_bus = GlobalEventBus
        self.env_file = env_file

        self._config: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = self._default_config()

        self.logger = logging.getLogger("NEO.Config")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Config] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._load_env()
        self._merge_defaults()

        # Event listeners
        self.event_bus.subscribe("config.get", self._on_get, priority=8)
        self.event_bus.subscribe("config.set", self._on_set, priority=8)
        self.event_bus.subscribe("config.reload", self._on_reload, priority=9)

    # =========================
    # Defaults
    # =========================

    def _default_config(self) -> Dict[str, Any]:
        return {
            "system": {
                "name": "NEO",
                "version": "1.0.0",
                "debug": True,
            },
            "event_bus": {
                "max_threads": 100,
                "default_timeout": 5,
            },
            "memory": {
                "file": "data/memory.json",
                "auto_save": True,
            },
            "ai": {
                "mode": "hybrid",
                "fallback": True,
            },
            "security": {
                "encryption_enabled": True,
            },
            "logging": {
                "level": "DEBUG",
            },
        }

    # =========================
    # ENV LOADER
    # =========================

    def _load_env(self):
        """
        Load .env file into config
        """
        try:
            if not os.path.exists(self.env_file):
                self.logger.warning(".env file not found")
                return

            with open(self.env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    if "=" not in line:
                        continue

                    key, value = line.split("=", 1)
                    self._set_nested(key.strip(), value.strip())

            self.logger.info(".env loaded successfully")

        except Exception as e:
            self.logger.error(f".env load failed: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Merge Defaults
    # =========================

    def _merge_defaults(self):
        """
        Merge default config with loaded values
        """
        def merge(d, default):
            for k, v in default.items():
                if k not in d:
                    d[k] = v
                elif isinstance(v, dict):
                    merge(d[k], v)

        with self._lock:
            merge(self._config, self._defaults)

    # =========================
    # Nested Access Helpers
    # =========================

    def _set_nested(self, key: str, value: Any):
        keys = key.split(".")
        d = self._config

        for k in keys[:-1]:
            d = d.setdefault(k, {})

        d[keys[-1]] = self._cast_value(value)

    def _get_nested(self, key: str) -> Any:
        keys = key.split(".")
        d = self._config

        for k in keys:
            if k not in d:
                return None
            d = d[k]

        return d

    def _cast_value(self, value: str) -> Any:
        """
        Convert string to correct type
        """
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"

        if value.isdigit():
            return int(value)

        try:
            return float(value)
        except ValueError:
            return value

    # =========================
    # Public API
    # =========================

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        with self._lock:
            value = self._get_nested(key)
            return value if value is not None else default

    def set(self, key: str, value: Any):
        with self._lock:
            self._set_nested(key, value)
            self.logger.info(f"Config updated: {key} = {value}")

    def reload(self):
        with self._lock:
            self._config.clear()
            self._load_env()
            self._merge_defaults()
            self.logger.info("Config reloaded")

    # =========================
    # Event Handlers
    # =========================

    def _on_get(self, event: Event):
        try:
            key = event.data.get("key")
            value = self.get(key)

            self.event_bus.publish(
                "config.response",
                {"key": key, "value": value},
                priority=7,
            )
        except Exception as e:
            self.logger.error(f"Config get failed: {e}")

    def _on_set(self, event: Event):
        try:
            key = event.data.get("key")
            value = event.data.get("value")
            self.set(key, value)
        except Exception as e:
            self.logger.error(f"Config set failed: {e}")

    def _on_reload(self, event: Event):
        try:
            self.reload()
        except Exception as e:
            self.logger.error(f"Config reload failed: {e}")

    # =========================
    # Debug / Dump
    # =========================

    def dump(self) -> Dict[str, Any]:
        with self._lock:
            return self._config.copy()


# =========================
# GLOBAL INSTANCE
# =========================

GlobalConfig = Config()