"""
logs/logger.py

NEO AI OS - Central Logging System

Responsibilities:
- Centralized logging across all modules
- Log to file + console
- Structured logging (JSON support)
- Log rotation
- Error tracking
- EventBus integration for critical logs

Features:
- Multi-level logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- File rotation (size-based)
- JSON logging option
- Thread-safe logging
- Automatic log directory creation
- Event-driven error reporting

"""

from __future__ import annotations

import os
import json
import logging
import traceback
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

from core.event_bus import GlobalEventBus


class LoggerManager:
    """
    Central logging manager.
    """

    def __init__(self, log_dir: str = "logs", json_mode: bool = False):
        self.event_bus = GlobalEventBus
        self.log_dir = log_dir
        self.json_mode = json_mode

        os.makedirs(self.log_dir, exist_ok=True)

        self.logger = logging.getLogger("NEO")
        self.logger.setLevel(logging.DEBUG)

        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    # =========================
    # Setup
    # =========================

    def _setup_handlers(self):
        log_file = os.path.join(self.log_dir, "neo.log")

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
        )

        console_handler = logging.StreamHandler()

        if self.json_mode:
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
            )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    # =========================
    # Logging Methods
    # =========================

    def log(self, level: str, message: str, extra: Dict[str, Any] = None):
        try:
            if self.json_mode:
                message = json.dumps({
                    "level": level,
                    "message": message,
                    "extra": extra or {},
                })

            if level == "debug":
                self.logger.debug(message)
            elif level == "info":
                self.logger.info(message)
            elif level == "warning":
                self.logger.warning(message)
            elif level == "error":
                self.logger.error(message)
                self._emit_error(message)
            elif level == "critical":
                self.logger.critical(message)
                self._emit_error(message)
            else:
                self.logger.info(message)

        except Exception as e:
            print("Logging failed:", e)

    def debug(self, msg: str):
        self.log("debug", msg)

    def info(self, msg: str):
        self.log("info", msg)

    def warning(self, msg: str):
        self.log("warning", msg)

    def error(self, msg: str):
        self.log("error", msg)

    def critical(self, msg: str):
        self.log("critical", msg)

    # =========================
    # Error Reporting
    # =========================

    def log_exception(self, e: Exception):
        tb = traceback.format_exc()
        self.error(f"{str(e)}\n{tb}")

    def _emit_error(self, message: str):
        try:
            self.event_bus.publish(
                "system.error.log",
                {"message": message},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalLogger = LoggerManager()