"""
system/system_monitor.py

NEO AI OS - System Monitor

Responsibilities:
- Monitor system-wide metrics (CPU, RAM, Disk, Network, Battery)
- Track historical metrics (rolling window)
- Detect threshold breaches and emit alerts
- Provide snapshots and summaries
- Background monitoring loop (configurable interval)
- Event-driven integration with EventBus

Features:
- Cross-platform metrics via psutil
- Rolling window history (deque)
- Threshold-based alerting
- Thread-safe operations
- Async + Sync APIs
- Graceful start/stop
- Detailed logging & error isolation

Dependencies:
pip install psutil
"""

from __future__ import annotations

import time
import threading
import logging
import traceback
import asyncio
from collections import deque
from typing import Dict, Any, Deque, Optional

import psutil

from core.event_bus import GlobalEventBus, Event


class SystemMonitorError(Exception):
    """Base exception for System Monitor"""


class SystemMonitor:
    """
    Monitors system health metrics and emits events.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        # Monitoring controls
        self.running: bool = False
        self.interval: float = 2.0  # seconds

        # History (rolling window)
        self.window_size: int = 60  # last 60 samples
        self.history: Dict[str, Deque[float]] = {
            "cpu": deque(maxlen=self.window_size),
            "ram": deque(maxlen=self.window_size),
            "disk": deque(maxlen=self.window_size),
            "net_sent": deque(maxlen=self.window_size),
            "net_recv": deque(maxlen=self.window_size),
        }

        # Thresholds (can be tuned via config later)
        self.thresholds: Dict[str, float] = {
            "cpu": 95.0,
            "ram": 95.0,
            "disk": 95.0,
        }

        # Baseline for network delta
        self._last_net = psutil.net_io_counters()

        self.logger = logging.getLogger("NEO.SystemMonitor")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [SystemMonitor] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("system.monitor.execute", self._on_execute, priority=9)
        self.event_bus.subscribe("system.monitor.start", self._start, priority=9)
        self.event_bus.subscribe("system.monitor.stop", self._stop, priority=9)
        self.event_bus.subscribe("system.monitor.snapshot", self._on_snapshot_request, priority=8)

    # =========================
    # Event Handlers
    # =========================

    def _on_execute(self, event: Event):
        """
        Handle commands routed by Brain.
        """
        try:
            cmd = (event.data.get("command") or "").lower()

            if "start" in cmd:
                self._start(event)
            elif "stop" in cmd:
                self._stop(event)
            elif "status" in cmd or "health" in cmd:
                snap = self.snapshot()
                self._emit_event("system.monitor.status", snap)
        except Exception as e:
            self._emit_error("execute", e)

    def _on_snapshot_request(self, event: Event):
        try:
            snap = self.snapshot()
            self._emit_event("system.monitor.snapshot.response", snap)
        except Exception as e:
            self._emit_error("snapshot_request", e)

    def _start(self, event: Event):
        with self._lock:
            if self.running:
                self.logger.warning("Monitor already running")
                return
            self.running = True
            threading.Thread(target=self._loop, daemon=True).start()
            self.logger.info("System monitoring started")
            self._emit_event("system.monitor.started", {"interval": self.interval})

    def _stop(self, event: Event):
        with self._lock:
            self.running = False
            self.logger.info("System monitoring stopped")
            self._emit_event("system.monitor.stopped", {})

    # =========================
    # Core Loop
    # =========================

    def _loop(self):
        while True:
            with self._lock:
                if not self.running:
                    break

            try:
                snap = self._collect()

                # Update history
                self._update_history(snap)

                # Threshold checks
                self._check_thresholds(snap)

                # Emit periodic update
                self._emit_event("system.monitor.tick", snap)

            except Exception as e:
                self._emit_error("monitor_loop", e)

            time.sleep(self.interval)

    # =========================
    # Data Collection
    # =========================

    def _collect(self) -> Dict[str, Any]:
        """
        Collect a snapshot of system metrics.
        """
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent

            net = psutil.net_io_counters()
            sent_delta = net.bytes_sent - self._last_net.bytes_sent
            recv_delta = net.bytes_recv - self._last_net.bytes_recv
            self._last_net = net

            battery_info = None
            try:
                battery = psutil.sensors_battery()
                if battery:
                    battery_info = {
                        "percent": battery.percent,
                        "plugged": battery.power_plugged,
                        "secs_left": battery.secsleft,
                    }
            except Exception:
                battery_info = None

            snapshot = {
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "network": {
                    "sent_bytes_delta": sent_delta,
                    "recv_bytes_delta": recv_delta,
                },
                "battery": battery_info,
                "timestamp": time.time(),
            }

            return snapshot

        except Exception as e:
            self._emit_error("collect", e)
            return {}

    def _update_history(self, snap: Dict[str, Any]):
        try:
            self.history["cpu"].append(snap.get("cpu", 0.0))
            self.history["ram"].append(snap.get("ram", 0.0))
            self.history["disk"].append(snap.get("disk", 0.0))
            net = snap.get("network", {})
            self.history["net_sent"].append(net.get("sent_bytes_delta", 0.0))
            self.history["net_recv"].append(net.get("recv_bytes_delta", 0.0))
        except Exception as e:
            self._emit_error("update_history", e)

    # =========================
    # Thresholds
    # =========================

    def _check_thresholds(self, snap: Dict[str, Any]):
        try:
            alerts = []

            if snap.get("cpu", 0) > self.thresholds["cpu"]:
                alerts.append(("cpu", snap.get("cpu")))
            if snap.get("ram", 0) > self.thresholds["ram"]:
                alerts.append(("ram", snap.get("ram")))
            if snap.get("disk", 0) > self.thresholds["disk"]:
                alerts.append(("disk", snap.get("disk")))

            for metric, value in alerts:
                self.logger.warning(f"Threshold breach: {metric}={value}")
                self._emit_event(
                    "system.monitor.alert",
                    {"metric": metric, "value": value, "threshold": self.thresholds.get(metric)},
                )

        except Exception as e:
            self._emit_error("check_thresholds", e)

    # =========================
    # Public APIs
    # =========================

    def snapshot(self) -> Dict[str, Any]:
        """
        Return current metrics snapshot.
        """
        try:
            return self._collect()
        except Exception as e:
            self._emit_error("snapshot", e)
            return {}

    def summary(self) -> Dict[str, Any]:
        """
        Return aggregated stats (avg over window).
        """
        try:
            with self._lock:
                def avg(dq: Deque[float]) -> float:
                    return (sum(dq) / len(dq)) if dq else 0.0

                return {
                    "avg_cpu": avg(self.history["cpu"]),
                    "avg_ram": avg(self.history["ram"]),
                    "avg_disk": avg(self.history["disk"]),
                    "avg_net_sent": avg(self.history["net_sent"]),
                    "avg_net_recv": avg(self.history["net_recv"]),
                    "samples": {
                        k: len(v) for k, v in self.history.items()
                    },
                }
        except Exception as e:
            self._emit_error("summary", e)
            return {}

    def set_threshold(self, metric: str, value: float) -> bool:
        with self._lock:
            try:
                if metric not in self.thresholds:
                    raise SystemMonitorError(f"Unknown metric: {metric}")
                self.thresholds[metric] = float(value)
                self.logger.info(f"Threshold updated: {metric}={value}")
                self._emit_event("system.monitor.threshold.updated", {"metric": metric, "value": value})
                return True
            except Exception as e:
                self._emit_error("set_threshold", e)
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
                "system.error.system_monitor",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async Wrappers
    # =========================

    async def snapshot_async(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self.snapshot)

    async def summary_async(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self.summary)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalSystemMonitor = SystemMonitor()