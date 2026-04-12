from __future__ import annotations

import os
import base64
import hashlib
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from core.event_bus import GlobalEventBus, Event


id = "security_encryption_manager"


class EncryptionError(Exception):
    """Encryption exception"""
    pass


class EncryptionManager:
    """
    Handles encryption/decryption securely.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.Encryption")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Encryption] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("security.encrypt", self._on_encrypt, priority=9)
        self.event_bus.subscribe("security.decrypt", self._on_decrypt, priority=9)

    # =========================
    # Key Management
    # =========================

    def generate_key(self) -> bytes:
        return Fernet.generate_key()

    def derive_key(self, password: str, salt: bytes) -> bytes:
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend(),
            )
            return base64.urlsafe_b64encode(kdf.derive(password.encode()))
        except Exception as e:
            self._error("derive_key", e)
            return b""

    # =========================
    # Encryption
    # =========================

    def encrypt_text(self, text: str, key: bytes) -> bytes:
        try:
            f = Fernet(key)
            return f.encrypt(text.encode())
        except Exception as e:
            self._error("encrypt_text", e)
            return b""

    def decrypt_text(self, token: bytes, key: bytes) -> str:
        try:
            f = Fernet(key)
            return f.decrypt(token).decode()
        except Exception as e:
            self._error("decrypt_text", e)
            return ""

    def encrypt_file(self, path: str, key: bytes) -> bool:
        try:
            with open(path, "rb") as f:
                data = f.read()

            encrypted = self.encrypt_text(data.decode(errors="ignore"), key)

            with open(path, "wb") as f:
                f.write(encrypted)

            self._emit("security.file.encrypted", {"path": path})
            return True

        except Exception as e:
            self._error("encrypt_file", e)
            return False

    def decrypt_file(self, path: str, key: bytes) -> bool:
        try:
            with open(path, "rb") as f:
                data = f.read()

            decrypted = self.decrypt_text(data, key)

            with open(path, "wb") as f:
                f.write(decrypted.encode())

            self._emit("security.file.decrypted", {"path": path})
            return True

        except Exception as e:
            self._error("decrypt_file", e)
            return False

    # =========================
    # Hashing
    # =========================

    def hash_sha256(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def hash_sha512(self, text: str) -> str:
        return hashlib.sha512(text.encode()).hexdigest()

    # =========================
    # Event Handlers
    # =========================

    def _on_encrypt(self, event: Event):
        try:
            text = event.data.get("text")
            password = event.data.get("password", "default")

            salt = os.urandom(16)
            key = self.derive_key(password, salt)

            encrypted = self.encrypt_text(text, key)

            self._emit(
                "security.encrypt.result",
                {
                    "encrypted": encrypted.decode(),
                    "salt": base64.b64encode(salt).decode(),
                },
            )

        except Exception as e:
            self._error("event_encrypt", e)

    def _on_decrypt(self, event: Event):
        try:
            token = event.data.get("token").encode()
            password = event.data.get("password")
            salt = base64.b64decode(event.data.get("salt"))

            key = self.derive_key(password, salt)

            decrypted = self.decrypt_text(token, key)

            self._emit("security.decrypt.result", {"decrypted": decrypted})

        except Exception as e:
            self._error("event_decrypt", e)

    # =========================
    # Helpers
    # =========================

    def _emit(self, name: str, data: Dict[str, Any]):
        try:
            self.event_bus.publish(name, data, priority=7)
        except Exception:
            pass

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.encryption",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def encrypt_text_async(self, text: str, key: bytes):
        return await asyncio.to_thread(self.encrypt_text, text, key)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalEncryptionManager = EncryptionManager()