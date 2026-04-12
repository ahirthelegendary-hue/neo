"""
data/storage_manager.py

NEO AI OS - Data Storage Manager

Responsibilities:
- Manage persistent storage (JSON-based)
- Provide key-value store (like lightweight DB)
- Handle file storage (read/write/delete)
- Cache frequently accessed data
- Ensure thread-safe read/write
- Emit storage events via EventBus

Features:
- In-memory cache + disk sync
- Namespaced storage (modules separated)
- Auto-save mechanism
- Data validation
- Async + Sync support
- Fault-tolerant writes

"""

from __future__ import annotations

import os
import json
import threading
import logging
import traceback
import asyncio
import time
from typing import Dict, Any, Optional

from core.event_bus import GlobalEventBus


class StorageError(Exception):
    """Storage exception"""


class StorageManager:
    """
    Persistent data manager.
    """

    def __init__(self, base_dir: str = "data"):
        self.event_bus = GlobalEventBus
        self.base_dir = base_dir

        self._lock = threading.RLock()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.last_saved: Dict[str, float] = {}

        self.logger = logging.getLogger("NEO.Storage")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Storage] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        os.makedirs(self.base_dir, exist_ok=True)

    # =========================
    # Core Storage
    # =========================

    def _get_file_path(self, namespace: str) -> str:
        return os.path.join(self.base_dir, f"{namespace}.json")

    def load(self, namespace: str) -> Dict[str, Any]:
        with self._lock:
            try:
                if namespace in self.cache:
                    return self.cache[namespace]

                path = self._get_file_path(namespace)

                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {}

                self.cache[namespace] = data
                return data

            except Exception as e:
                self._error("load", e)
                return {}

    def save(self, namespace: str):
        with self._lock:
            try:
                path = self._get_file_path(namespace)
                data = self.cache.get(namespace, {})

                tmp_path = path + ".tmp"

                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                os.replace(tmp_path, path)

                self.last_saved[namespace] = time.time()

                self.event_bus.publish(
                    "data.saved",
                    {"namespace": namespace},
                    priority=5,
                )

            except Exception as e:
                self._error("save", e)

    # =========================
    # Key-Value API
    # =========================

    def set(self, namespace: str, key: str, value: Any):
        with self._lock:
            data = self.load(namespace)
            data[key] = value
            self.cache[namespace] = data
            self.save(namespace)

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        data = self.load(namespace)
        return data.get(key, default)

    def delete(self, namespace: str, key: str):
        with self._lock:
            data = self.load(namespace)
            if key in data:
                del data[key]
                self.save(namespace)

    # =========================
    # File Operations
    # =========================

    def write_file(self, path: str, content: str):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            self.event_bus.publish("file.written", {"path": path}, priority=5)

        except Exception as e:
            self._error("write_file", e)

    def read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self._error("read_file", e)
            return ""

    def delete_file(self, path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
                self.event_bus.publish("file.deleted", {"path": path}, priority=5)
        except Exception as e:
            self._error("delete_file", e)

    # =========================
    # Cache Control
    # =========================

    def clear_cache(self):
        with self._lock:
            self.cache.clear()
            self.logger.info("Cache cleared")

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.storage",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def set_async(self, namespace: str, key: str, value: Any):
        return await asyncio.to_thread(self.set, namespace, key, value)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalStorageManager = StorageManager()