"""
system/file_manager.py

NEO AI OS - File Management Module

Responsibilities:
- Create, delete, rename, move files/folders
- Read/write file contents
- Search files (recursive)
- Detect duplicates (hash-based)
- Basic encryption/decryption (symmetric)
- Safe operations with validation
- Emit events via EventBus

Features:
- Cross-platform support
- Thread-safe operations
- Hash-based duplicate detection (SHA256)
- Safe overwrite controls
- Event-driven integration
- Async wrappers
- Detailed logging & error isolation
"""

from __future__ import annotations

import os
import shutil
import hashlib
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from core.event_bus import GlobalEventBus, Event


class FileManagerError(Exception):
    """Base exception for File Manager"""


class FileManager:
    """
    Handles file system operations safely.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.FileManager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [FileManager] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("system.file.execute", self._on_execute, priority=9)

    # =========================
    # Event Handler
    # =========================

    def _on_execute(self, event: Event):
        try:
            command = event.data.get("command", "")
            metadata = event.data.get("metadata", {})
            entities = metadata.get("entities", {})

            file_name = entities.get("file")

            if "create" in command:
                self.create_file(file_name)

            elif "delete" in command:
                self.delete(file_name)

        except Exception as e:
            self._emit_error("execute", e)

    # =========================
    # Core Operations
    # =========================

    def create_file(self, path: str, content: str = "", overwrite: bool = False) -> bool:
        with self._lock:
            try:
                if not path:
                    raise FileManagerError("Invalid file path")

                if os.path.exists(path) and not overwrite:
                    raise FileManagerError("File already exists")

                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                self.logger.info(f"File created: {path}")
                self._emit_event("system.file.created", {"path": path})
                return True

            except Exception as e:
                self._emit_error("create_file", e)
                return False

    def read_file(self, path: str) -> Optional[str]:
        with self._lock:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = f.read()

                self._emit_event("system.file.read", {"path": path})
                return data

            except Exception as e:
                self._emit_error("read_file", e)
                return None

    def write_file(self, path: str, content: str, append: bool = False) -> bool:
        with self._lock:
            try:
                mode = "a" if append else "w"

                with open(path, mode, encoding="utf-8") as f:
                    f.write(content)

                self._emit_event("system.file.updated", {"path": path})
                return True

            except Exception as e:
                self._emit_error("write_file", e)
                return False

    def delete(self, path: str) -> bool:
        with self._lock:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

                self._emit_event("system.file.deleted", {"path": path})
                return True

            except Exception as e:
                self._emit_error("delete", e)
                return False

    def move(self, src: str, dest: str) -> bool:
        with self._lock:
            try:
                shutil.move(src, dest)
                self._emit_event("system.file.moved", {"src": src, "dest": dest})
                return True

            except Exception as e:
                self._emit_error("move", e)
                return False

    def rename(self, src: str, new_name: str) -> bool:
        with self._lock:
            try:
                base = os.path.dirname(src)
                dest = os.path.join(base, new_name)
                os.rename(src, dest)

                self._emit_event("system.file.renamed", {"src": src, "dest": dest})
                return True

            except Exception as e:
                self._emit_error("rename", e)
                return False

    # =========================
    # Search / Duplicate Detection
    # =========================

    def search(self, directory: str, keyword: str) -> List[str]:
        results = []

        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    if keyword.lower() in file.lower():
                        results.append(os.path.join(root, file))

            self._emit_event("system.file.search", {"keyword": keyword, "count": len(results)})
        except Exception as e:
            self._emit_error("search", e)

        return results

    def find_duplicates(self, directory: str) -> Dict[str, List[str]]:
        hashes: Dict[str, List[str]] = {}

        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    path = os.path.join(root, file)
                    file_hash = self._hash_file(path)

                    hashes.setdefault(file_hash, []).append(path)

            duplicates = {h: p for h, p in hashes.items() if len(p) > 1}

            self._emit_event("system.file.duplicates", {"count": len(duplicates)})
            return duplicates

        except Exception as e:
            self._emit_error("find_duplicates", e)
            return {}

    def _hash_file(self, path: str) -> str:
        hasher = hashlib.sha256()

        try:
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
        except Exception:
            return ""

        return hasher.hexdigest()

    # =========================
    # Encryption (Basic XOR)
    # =========================

    def encrypt(self, path: str, key: str) -> bool:
        return self._xor_transform(path, key, "encrypted")

    def decrypt(self, path: str, key: str) -> bool:
        return self._xor_transform(path, key, "decrypted")

    def _xor_transform(self, path: str, key: str, action: str) -> bool:
        try:
            data = open(path, "rb").read()
            key_bytes = key.encode()

            transformed = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data)])

            with open(path, "wb") as f:
                f.write(transformed)

            self._emit_event(f"system.file.{action}", {"path": path})
            return True

        except Exception as e:
            self._emit_error(action, e)
            return False

    # =========================
    # Helpers
    # =========================

    def _emit_event(self, name: str, data: Dict[str, Any]):
        try:
            self.event_bus.publish(name, data, priority=7)
        except Exception:
            pass

    def _emit_error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.file_manager",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async Wrappers
    # =========================

    async def create_file_async(self, *args, **kwargs):
        return await asyncio.to_thread(self.create_file, *args, **kwargs)

    async def delete_async(self, path: str):
        return await asyncio.to_thread(self.delete, path)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalFileManager = FileManager()