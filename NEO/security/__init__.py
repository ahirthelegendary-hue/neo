"""
security/__init__.py

NEO AI OS - Security Module Manager

Responsibilities:
- Initialize and manage all security subsystems
- Integrate Firewall, IDS, Encryption modules
- Handle lifecycle (start/stop)
- Track security metrics (threats, blocks, errors)
- EventBus integration

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event
from security.firewall_manager import GlobalFirewallManager
from security.intrusion_detection import GlobalIDS
from security.encryption_manager import GlobalEncryptionManager


class SecurityError(Exception):
    pass


class SecurityManager:
    def __init__(self):
        from security.intrusion_detection import GlobalIDS
        self.event_bus = GlobalEventBus

        self.firewall = GlobalFirewallManager
        self.ids = GlobalIDS
        self.encryption = GlobalEncryptionManager

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.threats_detected: int = 0
        self.blocks: int = 0
        self.errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.Security.Manager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Security.Manager] %(message)s"
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

                self.start_time = time.time()
                self._running = True

                self.logger.info("Security Manager started")
                return True

            except Exception as e:
                self._error("start", e)
                return False

    def stop(self) -> bool:
        with self._lock:
            try:
                if not self._running:
                    return False

                self._running = False
                self.logger.info("Security Manager stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics
    # =========================

    def _inc_threat(self):
        with self._lock:
            self.threats_detected += 1

    def _inc_block(self):
        with self._lock:
            self.blocks += 1

    def _inc_error(self):
        with self._lock:
            self.errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            return {
                "status": "running" if self._running else "stopped",
                "uptime": round(uptime, 2),
                "threats_detected": self.threats_detected,
                "blocks": self.blocks,
                "errors": self.errors,
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("security.threat.detected", self._on_threat, priority=9)
            self.event_bus.subscribe("security.block", self._on_block, priority=9)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_threat(self, event: Event):
        try:
            self._inc_threat()
        except Exception as e:
            self._error("threat_event", e)

    def _on_block(self, event: Event):
        try:
            self._inc_block()
        except Exception as e:
            self._error("block_event", e)

    def _on_shutdown(self, event: Event):
        try:
            self.stop()
        except Exception as e:
            self._error("shutdown_event", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self._inc_error()

        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.security_manager",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalSecurityManager = SecurityManager()

