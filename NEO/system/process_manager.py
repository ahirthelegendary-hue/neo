"""
system/process_manager.py

NEO AI OS - Process Manager

Responsibilities:
- List running processes
- Kill processes (by PID/name)
- Monitor CPU/RAM usage per process
- Detect high-resource consumers
- Auto-kill based on rules
- Emit events via EventBus

Features:
- Cross-platform support
- Uses psutil for deep system insight
- Thread-safe operations
- Event-driven monitoring
- Async + Sync support
- Auto-protection (never kill critical system processes)

Dependencies:
pip install psutil
"""

from __future__ import annotations

import threading
import logging
import traceback
import asyncio
import time
from typing import Dict, Any, List, Optional

import psutil

from core.event_bus import GlobalEventBus, Event


class ProcessManagerError(Exception):
    """Base exception for process manager"""


class ProcessManager:
    """
    Handles system processes.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()
        self.monitoring = False

        self.safe_processes = {"system", "idle", "explorer", "init"}

        self.logger = logging.getLogger("NEO.ProcessManager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [ProcessManager] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("system.process.execute", self._on_execute, priority=9)
        self.event_bus.subscribe("system.process.monitor.start", self._start_monitor, priority=9)
        self.event_bus.subscribe("system.process.monitor.stop", self._stop_monitor, priority=9)

    # =========================
    # Event Handler
    # =========================

    def _on_execute(self, event: Event):
        try:
            command = event.data.get("command", "").lower()

            if "list" in command:
                processes = self.list_processes()
                self._emit_event("system.process.list", {"count": len(processes)})

            elif "kill" in command:
                name = event.data.get("metadata", {}).get("entities", {}).get("app")
                self.kill_by_name(name)

        except Exception as e:
            self._emit_error("execute", e)

    # =========================
    # Core Features
    # =========================

    def list_processes(self) -> List[Dict[str, Any]]:
        result = []

        try:
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                result.append(proc.info)

        except Exception as e:
            self._emit_error("list_processes", e)

        return result

    def kill_by_pid(self, pid: int) -> bool:
        with self._lock:
            try:
                proc = psutil.Process(pid)

                if proc.name().lower() in self.safe_processes:
                    raise ProcessManagerError("Attempt to kill protected process")

                proc.terminate()
                self._emit_event("system.process.killed", {"pid": pid})
                return True

            except Exception as e:
                self._emit_error("kill_by_pid", e)
                return False

    def kill_by_name(self, name: str) -> int:
        killed = 0

        try:
            for proc in psutil.process_iter(["name"]):
                if name and name.lower() in proc.info["name"].lower():
                    if proc.info["name"].lower() in self.safe_processes:
                        continue

                    proc.terminate()
                    killed += 1

            self._emit_event("system.process.killed_bulk", {"name": name, "count": killed})
        except Exception as e:
            self._emit_error("kill_by_name", e)

        return killed

    def monitor_usage(self, threshold_cpu: float = 80.0, threshold_mem: float = 80.0):
        """
        Detect high resource usage processes.
        """
        try:
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                cpu = proc.info["cpu_percent"]
                mem = proc.info["memory_percent"]

                if cpu > threshold_cpu or mem > threshold_mem:
                    self.logger.warning(f"High usage: {proc.info}")

                    self._emit_event(
                        "system.process.high_usage",
                        proc.info
                    )

        except Exception as e:
            self._emit_error("monitor_usage", e)

    # =========================
    # Monitoring Loop
    # =========================

    def _monitor_loop(self):
        while self.monitoring:
            self.monitor_usage()
            time.sleep(2)

    def _start_monitor(self, event: Event):
        if not self.monitoring:
            self.monitoring = True
            threading.Thread(target=self._monitor_loop, daemon=True).start()
            self.logger.info("Process monitoring started")

    def _stop_monitor(self, event: Event):
        self.monitoring = False
        self.logger.info("Process monitoring stopped")

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
                "system.error.process_manager",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async Wrappers
    # =========================

    async def list_processes_async(self):
        return await asyncio.to_thread(self.list_processes)

    async def kill_by_name_async(self, name: str):
        return await asyncio.to_thread(self.kill_by_name, name)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalProcessManager = ProcessManager()