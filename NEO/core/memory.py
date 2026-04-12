"""
core/memory.py

NEO AI OS - Persistent Memory Engine

Responsibilities:
- Store and retrieve structured data
- Maintain short-term and long-term memory
- Provide thread-safe read/write operations
- Persist memory to disk (JSON-based)
- Support namespacing (context separation)
- Provide TTL-based memory expiration
- Integrate with EventBus for updates

Features:
- In-memory + disk persistence
- Namespaced storage
- TTL support
- Thread-safe operations
- Auto-save & recovery
- Event-driven updates
- Fault tolerance

"""

from __future__ import annotations

import json
import os
import threading
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from core.event_bus import GlobalEventBus, Event


class MemoryError(Exception):
    """Base exception for memory system"""


class Memory:
    """
    Central memory system for NEO.
    """

    def __init__(self, file_path: str = "data/memory.json"):
        self.file_path = file_path
        self._lock = threading.RLock()
        self.event_bus = GlobalEventBus

        self.memory: Dict[str, Dict[str, Any]] = {}
        self.ttl_map: Dict[str, datetime] = {}

        self.logger = logging.getLogger("NEO.Memory")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Memory] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._ensure_file()
        self._load()

        # Subscribe to updates
        self.event_bus.subscribe("memory.set", self._on_memory_set, priority=8)
        self.event_bus.subscribe("memory.get", self._on_memory_get, priority=8)
        self.event_bus.subscribe("memory.delete", self._on_memory_delete, priority=8)

    # =========================
    # File Handling
    # =========================

    def _ensure_file(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            if not os.path.exists(self.file_path):
                with open(self.file_path, "w") as f:
                    json.dump({}, f)
        except Exception as e:
            self.logger.error(f"File init failed: {e}")
            self.logger.debug(traceback.format_exc())

    def _load(self):
        try:
            with open(self.file_path, "r") as f:
                self.memory = json.load(f)
        except Exception as e:
            self.logger.error(f"Load failed: {e}")
            self.memory = {}

    def _save(self):
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            self.logger.error(f"Save failed: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Core API
    # =========================

    def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if namespace not in self.memory:
                self.memory[namespace] = {}

            self.memory[namespace][key] = value

            if ttl:
                self.ttl_map[f"{namespace}.{key}"] = datetime.utcnow() + timedelta(seconds=ttl)

            self._save()

            self.logger.info(f"Set memory: {namespace}.{key}")

    def get(self, namespace: str, key: str) -> Optional[Any]:
        with self._lock:
            full_key = f"{namespace}.{key}"

            # TTL check
            if full_key in self.ttl_map:
                if datetime.utcnow() > self.ttl_map[full_key]:
                    self.logger.info(f"Memory expired: {full_key}")
                    self.delete(namespace, key)
                    return None

            return self.memory.get(namespace, {}).get(key)

    def delete(self, namespace: str, key: str):
        with self._lock:
            try:
                if namespace in self.memory and key in self.memory[namespace]:
                    del self.memory[namespace][key]

                full_key = f"{namespace}.{key}"
                if full_key in self.ttl_map:
                    del self.ttl_map[full_key]

                self._save()

                self.logger.info(f"Deleted memory: {namespace}.{key}")
            except Exception as e:
                self.logger.error(f"Delete failed: {e}")
                self.logger.debug(traceback.format_exc())

    def clear_namespace(self, namespace: str):
        with self._lock:
            if namespace in self.memory:
                del self.memory[namespace]
                self._save()
                self.logger.info(f"Cleared namespace: {namespace}")

    def clear_all(self):
        with self._lock:
            self.memory.clear()
            self.ttl_map.clear()
            self._save()
            self.logger.warning("All memory cleared")

    # =========================
    # Event Handlers
    # =========================

    def _on_memory_set(self, event: Event):
        try:
            data = event.data
            self.set(
                namespace=data.get("namespace", "default"),
                key=data["key"],
                value=data["value"],
                ttl=data.get("ttl"),
            )
        except Exception as e:
            self.logger.error(f"Event set failed: {e}")

    def _on_memory_get(self, event: Event):
        try:
            data = event.data
            value = self.get(
                namespace=data.get("namespace", "default"),
                key=data["key"],
            )

            # Send response event
            self.event_bus.publish(
                "memory.response",
                {"key": data["key"], "value": value},
                priority=7,
            )
        except Exception as e:
            self.logger.error(f"Event get failed: {e}")

    def _on_memory_delete(self, event: Event):
        try:
            data = event.data
            self.delete(
                namespace=data.get("namespace", "default"),
                key=data["key"],
            )
        except Exception as e:
            self.logger.error(f"Event delete failed: {e}")

    # =========================
    # Debug / Stats
    # =========================

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "namespaces": len(self.memory),
                "total_keys": sum(len(v) for v in self.memory.values()),
                "ttl_entries": len(self.ttl_map),
            }


# =========================
# GLOBAL INSTANCE
# =========================

GlobalMemory = Memory()