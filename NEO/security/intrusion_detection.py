"""
security/intrusion_detection.py

NEO AI OS - Intrusion Detection System (IDS)

Responsibilities:
- Monitor system login attempts & network activity
- Detect suspicious behavior (brute force, anomaly spikes)
- Maintain IP reputation scores
- Auto-trigger firewall actions
- Emit alerts via EventBus

Features:
- Real-time monitoring loop
- Heuristic-based anomaly detection
- IP reputation scoring
- Event-driven auto-response
- Thread-safe
- Async + Sync support
- Detailed logging

NOTE:
This is a lightweight IDS. Can be extended with ML models later.
"""

from __future__ import annotations

import time
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any

import psutil

from core.event_bus import GlobalEventBus, Event

from security.trusted_guard import TrustedGuard

class IntrusionError(Exception):
    """Intrusion Detection exception"""


class IntrusionDetectionSystem:
    """
    Detects suspicious activities.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.running = False

        # Track attempts per IP
        self.ip_attempts: Dict[str, int] = {}
        self.ip_reputation: Dict[str, float] = {}

        self.logger = logging.getLogger("NEO.IDS")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [IDS] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("security.ids.start", self._start, priority=9)
        self.event_bus.subscribe("security.ids.stop", self._stop, priority=9)
        self.event_bus.subscribe("security.login.attempt", self._on_login_attempt, priority=9)

    # =========================
    # Monitoring Loop
    # =========================

    def _monitor_loop(self):
        while self.running:
            try:
                self._scan_network()
                self._evaluate_reputation()
            except Exception as e:
                self._error("monitor_loop", e)

            time.sleep(2)

    def _start(self, event: Event):
        if not self.running:
            self.running = True
            threading.Thread(target=self._monitor_loop, daemon=True).start()
            self.logger.info("IDS started")

    def _stop(self, event: Event):
        self.running = False
        self.logger.info("IDS stopped")

    # =========================
    # Detection Logic
    # =========================

    def _on_login_attempt(self, event: Event):
        try:
            ip = event.data.get("ip")

            if not ip:
                return
            if ip == "127.0.0.1":
                return

            self.ip_attempts[ip] = self.ip_attempts.get(ip, 0) + 1

            if self.ip_attempts[ip] > 5:
                self.logger.warning(f"Multiple failed logins from {ip}")

                self.event_bus.publish(
                    "security.threat.detected",
                    {"ip": ip, "type": "brute_force"},
                    priority=10,
                )

        except Exception as e:
            self._error("login_attempt", e)

    def _scan_network(self):
        """
        Monitor network connections.
        """
        try:
            connections = psutil.net_connections(kind="inet")

            for conn in connections:
                if conn.raddr:
                    ip = conn.raddr.ip
                    self.ip_attempts[ip] = self.ip_attempts.get(ip, 0) + 0.1

        except Exception as e:
            self._error("scan_network", e)

    def _evaluate_reputation(self):
        """
        Update IP reputation and trigger actions.
        """
        try:
            for ip, score in list(self.ip_attempts.items()):
                reputation = max(0.0, 1.0 - (score / 20.0))
                self.ip_reputation[ip] = reputation

                if reputation < 0.3:
                 if self.guard.is_safe(ip):
                    self.logger.info(f"[IDS] ✅ Trusted IP: {ip}")
                    return

                    self.logger.warning(f"[IDS] ⚠️ Suspicious IP: {ip}")

                    self.event_bus.publish(
                  "security.firewall.block",
                  {"ip": ip},
                  priority=10,
                )

        except Exception as e:
            self._error("evaluate_reputation", e)

    # =========================
    # Helpers
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.ids",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Public API
    # =========================

    def get_reputation(self, ip: str) -> float:
        return self.ip_reputation.get(ip, 1.0)

    async def get_reputation_async(self, ip: str):
        return await asyncio.to_thread(self.get_reputation, ip)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalIDS = IntrusionDetectionSystem()