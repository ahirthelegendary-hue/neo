"""
core/command_parser.py

NEO AI OS - Command Parser Engine

Responsibilities:
- Parse raw user input (text/voice) into structured commands
- Normalize and clean input
- Extract entities (app names, file names, intents, etc.)
- Generate metadata for Brain
- Detect command type (system, ai, devops, etc.)
- Handle multi-command input
- Provide fallback handling
- Emit parsed events to EventBus

Features:
- NLP-lite parsing (rule-based, extendable to ML later)
- Multi-command splitting
- Entity extraction
- Confidence scoring
- Error handling
- Async + Sync support
- Event-driven integration

"""

from __future__ import annotations

import re
import asyncio
import logging
import threading
import traceback
from typing import Dict, Any, List, Optional

from core.event_bus import GlobalEventBus, Event


class CommandParserError(Exception):
    """Base exception for Command Parser"""


class CommandParser:
    """
    Parses raw commands into structured data for Brain.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.CommandParser")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [CommandParser] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Subscribe to input events
        self.event_bus.subscribe("voice.command", self._on_raw_input, priority=9)
        self.event_bus.subscribe("text.command", self._on_raw_input, priority=9)

    # =========================
    # Event Entry
    # =========================

    def _on_raw_input(self, event: Event):
        """
        Handle raw input from voice/text modules.
        """
        try:
            raw = event.data.get("text", "").strip()

            if not raw:
                self.logger.warning("Empty input received")
                return

            self.logger.info(f"Raw input: {raw}")

            commands = self._split_commands(raw)

            for cmd in commands:
                parsed = self._parse_command(cmd)

                self.event_bus.publish(
                    "command.received",
                    {
                        "command": parsed["clean_text"],
                        "metadata": parsed,
                    },
                    priority=9,
                )

        except Exception as e:
            self.logger.error(f"Parsing failed: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Core Parsing Logic
    # =========================

    def _split_commands(self, text: str) -> List[str]:
        """
        Split multiple commands (e.g., 'open chrome and check cpu')
        """
        parts = re.split(r"\band\b|\bthen\b|,", text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    def _clean_text(self, text: str) -> str:
        """
        Normalize text
        """
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text.strip()

    def _parse_command(self, text: str) -> Dict[str, Any]:
        """
        Convert raw text into structured metadata
        """
        clean = self._clean_text(text)

        entities = self._extract_entities(clean)
        intent = self._detect_intent(clean)
        confidence = self._confidence_score(clean, intent)

        parsed = {
            "original": text,
            "clean_text": clean,
            "intent_hint": intent,
            "entities": entities,
            "confidence": confidence,
        }

        self.logger.debug(f"Parsed: {parsed}")
        return parsed

    # =========================
    # Entity Extraction
    # =========================

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract useful entities from command.
        """
        entities = {}

        # App names
        apps = ["chrome", "vscode", "notepad", "spotify", "edge"]
        for app in apps:
            if app in text:
                entities["app"] = app

        # File names
        file_match = re.findall(r"\b\w+\.(txt|py|json|log)\b", text)
        if file_match:
            entities["file"] = file_match

        # Numbers
        numbers = re.findall(r"\b\d+\b", text)
        if numbers:
            entities["numbers"] = [int(n) for n in numbers]

        # Keywords
        if "cpu" in text or "ram" in text:
            entities["metric"] = "system"

        return entities

    # =========================
    # Intent Detection
    # =========================

    def _detect_intent(self, text: str) -> str:
        """
        Rough intent detection (Brain will refine).
        """
        if any(x in text for x in ["open", "launch", "start"]):
            return "system.app_control"

        if any(x in text for x in ["delete", "remove"]):
            return "system.file.delete"

        if any(x in text for x in ["create", "make"]):
            return "system.file.create"

        if any(x in text for x in ["cpu", "ram", "usage"]):
            return "system.monitor"

        if any(x in text for x in ["face", "camera"]):
            return "vision.detect"

        if any(x in text for x in ["code", "bug", "error"]):
            return "devops.analyze"

        if any(x in text for x in ["secure", "encrypt"]):
            return "security.action"

        return "ai.general"

    # =========================
    # Confidence Score
    # =========================

    def _confidence_score(self, text: str, intent: str) -> float:
        """
        Simple scoring logic
        """
        score = 0.5

        if intent != "ai.general":
            score += 0.3

        if len(text.split()) > 3:
            score += 0.1

        if any(word in text for word in ["please", "now", "quick"]):
            score += 0.05

        return min(score, 1.0)

    # =========================
    # Public API
    # =========================

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Direct parse API
        """
        return self._parse_command(text)

    async def parse_async(self, text: str) -> Dict[str, Any]:
        """
        Async parse API
        """
        return await asyncio.to_thread(self._parse_command, text)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalCommandParser = CommandParser()