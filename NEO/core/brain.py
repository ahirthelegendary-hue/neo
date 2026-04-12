"""
core/brain.py

NEO AI OS - Central Brain Engine

This module acts as the orchestrator of the entire system.
Responsibilities:
- Receive parsed commands from CommandParser
- Decide intent routing
- Dispatch events via EventBus
- Maintain context awareness
- Handle fallback logic
- Coordinate modules (AI, System, Vision, etc.)
- Maintain execution state

Features:
- Event-driven orchestration
- Context-aware decision making
- Priority routing
- Async + Sync execution
- Failure isolation
- Intelligent fallback system
- Deep logging + tracing
"""

from __future__ import annotations

import asyncio
import threading
import logging
import traceback
from typing import Dict, Any, Optional

from core.event_bus import GlobalEventBus, Event


class BrainError(Exception):
    """Base exception for Brain"""


class Brain:
    """
    Central orchestration engine of NEO.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self.context: Dict[str, Any] = {}
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.Brain")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Brain] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Register internal listeners
        self._register_internal_events()

    # =========================
    # Setup
    # =========================

    def _register_internal_events(self):
        """
        Subscribe to key system events.
        """
        self.event_bus.subscribe("command.received", self._on_command_received, priority=9)
        self.event_bus.subscribe("system.error.*", self._on_system_error, priority=9)
        self.event_bus.subscribe("brain.context.update", self._update_context, priority=8)

    # =========================
    # Event Handlers
    # =========================

    def _on_command_received(self, event: Event):
        """
        Handle incoming commands from parser.
        """
        try:
            command = event.data.get("command")
            metadata = event.data.get("metadata", {})

            if not command:
                self.logger.warning("Empty command received")
                return

            self.logger.info(f"Processing command: {command}")

            # Route command
            intent = self._classify_intent(command)

            self.logger.debug(f"Detected intent: {intent}")

            self._route_intent(intent, command, metadata)

        except Exception as e:
            self.logger.error(f"Command processing failed: {e}")
            self.logger.debug(traceback.format_exc())

    def _on_system_error(self, event: Event):
        """
        Handle system-level errors.
        """
        self.logger.error(f"System Error Received: {event.data}")

    def _update_context(self, event: Event):
        """
        Update internal memory context.
        """
        with self._lock:
            self.context.update(event.data)
            self.logger.debug(f"Context updated: {event.data}")

    # =========================
    # Intent Engine
    # =========================

    def _classify_intent(self, command: str) -> str:
        """
        Basic intent classification (expandable).
        """
        command = command.lower()

        if any(x in command for x in ["open", "launch", "start"]):
            return "system.app_control"

        if any(x in command for x in ["file", "delete", "create", "rename"]):
            return "system.file"

        if any(x in command for x in ["cpu", "ram", "status", "health"]):
            return "system.monitor"

        if any(x in command for x in ["face", "detect", "camera"]):
            return "vision.detect"

        if any(x in command for x in ["code", "bug", "error"]):
            return "devops.analyze"

        if any(x in command for x in ["secure", "encrypt", "firewall"]):
            return "security.action"

        if any(x in command for x in ["schedule", "task", "reminder"]):
            return "automation.task"

        return "ai.general"

    # =========================
    # Routing Engine
    # =========================

    def _route_intent(self, intent: str, command: str, metadata: Dict[str, Any]):
        """
        Dispatch command to correct subsystem.
        """
        try:
            event_name = f"{intent}.execute"

            payload = {
                "command": command,
                "metadata": metadata,
                "context": self.context.copy(),
            }

            self.logger.info(f"Dispatching to: {event_name}")

            self.event_bus.publish(event_name, payload, priority=7)

        except Exception as e:
            self.logger.error(f"Routing failed: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Public API
    # =========================

    def process(self, command: str):
        """
        External entry point.
        """
        try:
            self.event_bus.publish(
                "command.received",
                {"command": command, "metadata": {}},
                priority=9,
            )
        except Exception as e:
            self.logger.error(f"Process failed: {e}")

    async def process_async(self, command: str):
        """
        Async version.
        """
        try:
            await self.event_bus.publish_async(
                "command.received",
                {"command": command, "metadata": {}},
                priority=9,
            )
        except Exception as e:
            self.logger.error(f"Async process failed: {e}")

    # =========================
    # Context API
    # =========================

    def get_context(self) -> Dict[str, Any]:
        with self._lock:
            return self.context.copy()

    def clear_context(self):
        with self._lock:
            self.context.clear()
            self.logger.info("Context cleared")


# =========================
# GLOBAL INSTANCE
# =========================

GlobalBrain = Brain()