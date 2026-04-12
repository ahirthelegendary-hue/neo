"""
ai/response_generator.py

NEO AI OS - Response Generator

Responsibilities:
- Generate human-like responses
- Convert AI decisions into natural language
- Support multiple tones (formal, casual, sarcastic, etc.)
- Context-aware replies
- Integrate with EventBus

Features:
- Template-based + dynamic responses
- Tone switching
- Context memory support
- Async + Sync
- Event-driven

"""

from __future__ import annotations

import random
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event


class ResponseGeneratorError(Exception):
    """Response Generator exception"""


class ResponseGenerator:
    """
    Converts AI outputs into human responses.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.Response")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Response] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Tone styles
        self.tones = {
            "normal": [
                "Done.",
                "Task completed.",
                "Here you go.",
            ],
            "friendly": [
                "Got it boss 😎",
                "Done bro 🔥",
                "Ho gaya 👍",
            ],
            "jarvis": [
                "Task executed successfully, sir.",
                "As you wish.",
                "Operation complete.",
            ]
        }

        # Event subscription
        self.event_bus.subscribe("ai.response.generate", self._on_generate, priority=9)

    # =========================
    # Core Generation
    # =========================

    def generate(self, data: Dict[str, Any]) -> str:
        try:
            intent = data.get("intent", "general")
            tone = data.get("tone", "jarvis")

            base_response = self._intent_response(intent, data)

            style = random.choice(self.tones.get(tone, self.tones["normal"]))

            final = f"{style} {base_response}".strip()

            return final

        except Exception as e:
            self._error("generate", e)
            return "Something went wrong."

    def _intent_response(self, intent: str, data: Dict[str, Any]) -> str:
        """
        Generate response based on intent.
        """

        if intent == "system.app":
            app = data.get("entities", {}).get("app", "application")
            return f"{app} opened."

        if intent == "system.file":
            return "File operation completed."

        if intent == "system.monitor":
            return "System status updated."

        if intent == "security":
            return "Security scan completed."

        if intent == "devops":
            return "Code analysis done."

        return "Request processed."

    # =========================
    # Event Handler
    # =========================

    def _on_generate(self, event: Event):
        try:
            response = self.generate(event.data)

            self.event_bus.publish(
                "ai.response.ready",
                {"response": response},
                priority=8,
            )

            self.logger.info(f"Response: {response}")

        except Exception as e:
            self._error("event_generate", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.response",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def generate_async(self, data: Dict[str, Any]):
        return await asyncio.to_thread(self.generate, data)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalResponseGenerator = ResponseGenerator()