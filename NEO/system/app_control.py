"""
system/app_control.py

NEO AI OS - Application Control Module

Responsibilities:
- Open/close applications cross-platform
- Focus/activate running applications
- Kill processes by name/pid
- Launch URLs in default browser
- Maintain app aliases (e.g., "chrome" -> executable path)
- Emit lifecycle events via EventBus

Features:
- Cross-platform support (Windows/Linux/macOS)
- Safe execution with detailed error handling
- Process discovery & filtering
- Priority-based event handling
- Async wrappers for non-blocking calls
- Logging & telemetry

Dependencies:
- Python standard library only (subprocess, os, sys, shutil)
"""

from __future__ import annotations

import os
import sys
import shlex
import shutil
import signal
import asyncio
import logging
import traceback
import subprocess
import threading
from typing import Dict, Any, List, Optional

from core.event_bus import GlobalEventBus, Event


class AppControlError(Exception):
    """Base exception for App Control"""


class AppController:
    """
    Controls applications: open, close, focus, URL launch.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        # Common aliases -> executable/command
        self.aliases: Dict[str, str] = self._default_aliases()

        self.logger = logging.getLogger("NEO.AppControl")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [AppControl] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("system.app_control.execute", self._on_execute, priority=9)
        self.event_bus.subscribe("system.app.open", self._on_open_event, priority=9)
        self.event_bus.subscribe("system.app.close", self._on_close_event, priority=9)
        self.event_bus.subscribe("system.app.kill", self._on_kill_event, priority=9)

    # =========================
    # Defaults
    # =========================

    def _default_aliases(self) -> Dict[str, str]:
        if sys.platform.startswith("win"):
            return {
                "chrome": "chrome",
                "edge": "msedge",
                "notepad": "notepad",
                "vscode": "code",
                "spotify": "spotify",
            }
        elif sys.platform.startswith("linux"):
            return {
                "chrome": "google-chrome",
                "firefox": "firefox",
                "vscode": "code",
                "terminal": "gnome-terminal",
            }
        else:  # macOS
            return {
                "chrome": "Google Chrome",
                "safari": "Safari",
                "vscode": "Visual Studio Code",
                "terminal": "Terminal",
            }

    # =========================
    # Event Handlers
    # =========================

    def _on_execute(self, event: Event):
        """
        Unified handler from Brain routing.
        """
        try:
            command = event.data.get("command", "")
            metadata = event.data.get("metadata", {})
            entities = metadata.get("entities", {})

            app = entities.get("app")
            if not app:
                self.logger.warning("No app found in command")
                return

            if any(k in command for k in ["open", "launch", "start"]):
                self.open_app(app)

            elif any(k in command for k in ["close", "stop", "exit"]):
                self.close_app(app)

        except Exception as e:
            self._emit_error("execute", e)

    def _on_open_event(self, event: Event):
        app = event.data.get("app")
        if app:
            self.open_app(app)

    def _on_close_event(self, event: Event):
        app = event.data.get("app")
        if app:
            self.close_app(app)

    def _on_kill_event(self, event: Event):
        name = event.data.get("name")
        pid = event.data.get("pid")
        self.kill_process(name=name, pid=pid)

    # =========================
    # Core Actions
    # =========================

    def open_app(self, app: str) -> bool:
        """
        Launch an application by alias or command.
        """
        with self._lock:
            try:
                cmd = self._resolve_app(app)
                if not cmd:
                    raise AppControlError(f"Unknown app: {app}")

                self.logger.info(f"Opening app: {app} -> {cmd}")

                if sys.platform.startswith("win"):
                    subprocess.Popen(cmd, shell=True)
                elif sys.platform.startswith("linux"):
                    subprocess.Popen(shlex.split(cmd))
                else:  # macOS
                    subprocess.Popen(["open", "-a", cmd])

                self._emit_event("system.app.opened", {"app": app, "cmd": cmd})
                return True

            except Exception as e:
                self._emit_error("open_app", e)
                return False

    def close_app(self, app: str) -> bool:
        """
        Close application by name.
        """
        with self._lock:
            try:
                self.logger.info(f"Closing app: {app}")

                if sys.platform.startswith("win"):
                    subprocess.run(["taskkill", "/IM", f"{app}.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif sys.platform.startswith("linux"):
                    subprocess.run(["pkill", "-f", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(["pkill", "-f", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                self._emit_event("system.app.closed", {"app": app})
                return True

            except Exception as e:
                self._emit_error("close_app", e)
                return False

    def kill_process(self, name: Optional[str] = None, pid: Optional[int] = None) -> bool:
        """
        Kill process by name or PID.
        """
        with self._lock:
            try:
                if pid:
                    os.kill(pid, signal.SIGTERM)
                    self.logger.info(f"Killed PID: {pid}")
                elif name:
                    if sys.platform.startswith("win"):
                        subprocess.run(["taskkill", "/IM", name, "/F"])
                    else:
                        subprocess.run(["pkill", "-f", name])
                    self.logger.info(f"Killed process: {name}")
                else:
                    raise AppControlError("No name or PID provided")

                self._emit_event("system.process.killed", {"name": name, "pid": pid})
                return True

            except Exception as e:
                self._emit_error("kill_process", e)
                return False

    def open_url(self, url: str) -> bool:
        """
        Open URL in default browser.
        """
        try:
            import webbrowser
            webbrowser.open(url)
            self._emit_event("system.url.opened", {"url": url})
            return True
        except Exception as e:
            self._emit_error("open_url", e)
            return False

    # =========================
    # Helpers
    # =========================

    def _resolve_app(self, app: str) -> Optional[str]:
        """
        Resolve alias to executable/command.
        """
        if app in self.aliases:
            return self.aliases[app]

        # Try direct resolution
        if shutil.which(app):
            return app

        return None

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
                "system.error.app_control",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async Wrappers
    # =========================

    async def open_app_async(self, app: str) -> bool:
        return await asyncio.to_thread(self.open_app, app)

    async def close_app_async(self, app: str) -> bool:
        return await asyncio.to_thread(self.close_app, app)

    async def kill_process_async(self, name: Optional[str] = None, pid: Optional[int] = None) -> bool:
        return await asyncio.to_thread(self.kill_process, name, pid)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalAppController = AppController()