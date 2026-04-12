"""
ai/learning.py

NEO AI OS - Learning Engine
"""

from __future__ import annotations

import json
import os
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any, List

from core.event_bus import GlobalEventBus, Event


class LearningError(Exception):
    pass


class LearningEngine:
    def __init__(self, memory_file: str = "data/learning.json"):
        self.event_bus = GlobalEventBus
        self.memory_file = memory_file

        self._lock = threading.RLock()
        self.knowledge: Dict[str, Any] = {}

        self.logger = logging.getLogger("NEO.Learning")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Learning] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._load()

        self.event_bus.subscribe("ai.learn", self._on_learn, priority=8)
        self.event_bus.subscribe("ai.feedback", self._on_feedback, priority=8)

    # =========================
    # Core Learning
    # =========================

    def learn(self, key: str, value: Any):
        with self._lock:
            self.knowledge[key] = value
            self._save()

    def recall(self, key: str) -> Any:
        return self.knowledge.get(key)

    def update(self, key: str, value: Any):
        with self._lock:
            if key in self.knowledge:
                self.knowledge[key] = value
                self._save()

    def delete(self, key: str):
        with self._lock:
            if key in self.knowledge:
                del self.knowledge[key]
                self._save()

    def all(self) -> Dict[str, Any]:
        return self.knowledge

    # =========================
    # Feedback Learning
    # =========================

    def feedback(self, data: Dict[str, Any]):
        try:
            key = data.get("input")
            correct = data.get("correct")

            if key and correct:
                self.learn(key, correct)

        except Exception as e:
            self._error("feedback", e)

    # =========================
    # Persistence
    # =========================

    def _load(self):
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self.knowledge = json.load(f)
        except Exception as e:
            self._error("load", e)

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)

            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.knowledge, f, indent=2)

        except Exception as e:
            self._error("save", e)

    # =========================
    # Event Handlers
    # =========================

    def _on_learn(self, event: Event):
        try:
            key = event.data.get("key")
            value = event.data.get("value")

            if key:
                self.learn(key, value)

        except Exception as e:
            self._error("event_learn", e)

    def _on_feedback(self, event: Event):
        self.feedback(event.data)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.learning",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def learn_async(self, key: str, value: Any):
        return await asyncio.to_thread(self.learn, key, value)


GlobalLearningEngine = LearningEngine()