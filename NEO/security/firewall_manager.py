"""
security/firewall_manager.py

NEO AI OS - Firewall Manager

Responsibilities:
- Block / allow IP addresses
- Maintain whitelist / blacklist
- Monitor suspicious connections
- Auto-block malicious IPs
- Emit alerts via EventBus
- Cross-platform command execution (Windows/Linux)

Features:
- Dynamic IP blocking
- Rule persistence (in-memory, extendable)
- Threat detection (basic heuristics)
- Event-driven security responses
- Async + Sync support
- Thread-safe

NOTE:
Requires admin/root privileges for actual firewall commands.
"""

from __future__ import annotations

import subprocess
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any, Set

from core.event_bus import GlobalEventBus, Event


class FirewallError(Exception):
    """Firewall exception"""


class FirewallManager:
    """
    Manage firewall rules dynamically.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.blocked_ips: Set[str] = set()
        self.allowed_ips: Set[str] = set()

        self.logger = logging.getLogger("NEO.Firewall")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Firewall] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("security.firewall.block", self._on_block, priority=9)
        self.event_bus.subscribe("security.firewall.allow", self._on_allow, priority=9)
        self.event_bus.subscribe("security.firewall.unblock", self._on_unblock, priority=9)

    # =========================
    # Core Functions
    # =========================

    def block_ip(self, ip: str) -> bool:
        with self._lock:
            try:
                if ip in self.blocked_ips:
                    return True

                self._apply_rule(ip, block=True)
                self.blocked_ips.add(ip)

                self._emit("security.firewall.blocked", {"ip": ip})
                return True

            except Exception as e:
                self._error("block_ip", e)
                return False

    def allow_ip(self, ip: str) -> bool:
        with self._lock:
            try:
                self.allowed_ips.add(ip)
                self._emit("security.firewall.allowed", {"ip": ip})
                return True

            except Exception as e:
                self._error("allow_ip", e)
                return False

    def unblock_ip(self, ip: str) -> bool:
        with self._lock:
            try:
                if ip in self.blocked_ips:
                    self._apply_rule(ip, block=False)
                    self.blocked_ips.remove(ip)

                self._emit("security.firewall.unblocked", {"ip": ip})
                return True

            except Exception as e:
                self._error("unblock_ip", e)
                return False

    # =========================
    # OS Commands
    # =========================

    def _apply_rule(self, ip: str, block: bool):
        """
        Apply firewall rule based on OS.
        """
        try:
            if block:
                if self._is_windows():
                    subprocess.run(f"netsh advfirewall firewall add rule name=Block_{ip} dir=in action=block remoteip={ip}", shell=True)
                else:
                    subprocess.run(["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"])
            else:
                if self._is_windows():
                    subprocess.run(f"netsh advfirewall firewall delete rule name=Block_{ip}", shell=True)
                else:
                    subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"])

        except Exception as e:
            self._error("apply_rule", e)

    def _is_windows(self) -> bool:
        import platform
        return platform.system().lower() == "windows"

    # =========================
    # Threat Detection
    # =========================

    def detect_threat(self, ip: str, attempts: int):
        """
        Simple brute-force detection.
        """
        if attempts > 10:
            self.logger.warning(f"Threat detected from {ip}")
            self.block_ip(ip)

    # =========================
    # Event Handlers
    # =========================

    def _on_block(self, event: Event):
        ip = event.data.get("ip")
        if ip:
            self.block_ip(ip)

    def _on_allow(self, event: Event):
        ip = event.data.get("ip")
        if ip:
            self.allow_ip(ip)

    def _on_unblock(self, event: Event):
        ip = event.data.get("ip")
        if ip:
            self.unblock_ip(ip)

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
                "system.error.firewall",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def block_ip_async(self, ip: str):
        return await asyncio.to_thread(self.block_ip, ip)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalFirewallManager = FirewallManager()