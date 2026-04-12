"""
ui/dashboard.py

NEO AI OS - Dashboard UI (Terminal-Based)

Responsibilities:
- Display real-time system overview
- Show metrics from all managers (API, System, Security, DevOps, UI)
- Refresh dashboard periodically
- Event-driven updates

Features:
- Threaded live dashboard
- Clean terminal rendering
- EventBus integration
- Auto refresh loop
- Error-safe rendering

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
import os
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event

from api.__init__ import GlobalAPIManager
from system.__init__ import GlobalSystemManager
from security.__init__ import GlobalSecurityManager
from devops.__init__ import GlobalDevOpsManager
from automation.__init__ import GlobalAutomationManager
from ui.__init__ import GlobalUIManager


class DashboardError(Exception):
    pass


class Dashboard:
    def __init__(self, refresh_interval: int = 2):
        self.event_bus = GlobalEventBus
        self.refresh_interval = refresh_interval

        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None

        self.logger = logging.getLogger("NEO.UI.Dashboard")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Dashboard] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._subscribe_events()

    # =========================
    # Lifecycle
    # =========================

    def start(self):
        with self._lock:
            if self._running:
                return

            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

            self.logger.info("Dashboard started")

    def stop(self):
        with self._lock:
            self._running = False
            self.logger.info("Dashboard stopped")

    # =========================
    # Loop
    # =========================

    def _loop(self):
        while self._running:
            try:
                self._render()
                time.sleep(self.refresh_interval)
            except Exception as e:
                self._error("loop", e)

    # =========================
    # Rendering
    # =========================

    def _render(self):
        os.system("cls" if os.name == "nt" else "clear")

        print("=" * 50)
        print("      NEO AI OS DASHBOARD")
        print("=" * 50)

        try:
            api = GlobalAPIManager.get_metrics()
            system = GlobalSystemManager.get_metrics()
            security = GlobalSecurityManager.get_metrics()
            devops = GlobalDevOpsManager.get_metrics()
            automation = GlobalAutomationManager.get_metrics()
            ui = GlobalUIManager.get_metrics()

            self._print_section("API", api)
            self._print_section("SYSTEM", system)
            self._print_section("SECURITY", security)
            self._print_section("DEVOPS", devops)
            self._print_section("AUTOMATION", automation)
            self._print_section("UI", ui)

        except Exception as e:
            self._error("render", e)

        print("=" * 50)

    def _print_section(self, name: str, data: Dict[str, Any]):
        print(f"\n[{name}]")
        for k, v in data.items():
            print(f"  {k}: {v}")

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("ui.dashboard.refresh", self._on_refresh, priority=7)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_refresh(self, event: Event):
        try:
            self._render()
        except Exception as e:
            self._error("refresh_event", e)

    def _on_shutdown(self, event: Event):
        try:
            self.stop()
        except Exception as e:
            self._error("shutdown_event", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.dashboard",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalDashboard = Dashboard()