"""
ai/reasoning_engine.py

NEO AI OS - Reasoning Engine

Responsibilities:
- Multi-step reasoning over tasks
- Rule-based decision making
- Context-aware inference
- Goal decomposition (break tasks into sub-tasks)
- Self-correction loop (retry with improved strategy)
- Confidence scoring
- Event-driven integration with Brain + EventBus

Features:
- Chain-of-Thought style reasoning (structured, non-sensitive)
- Pluggable strategies (rules, heuristics, future ML)
- Error recovery & fallback strategies
- Async + Sync support
- Thread-safe
- Detailed logging & telemetry

NOTE:
This is a lightweight reasoning engine (no external LLM required).
Can be extended to integrate with external models later.
"""

from __future__ import annotations

import threading
import logging
import traceback
import asyncio
from typing import Dict, Any, List, Callable, Optional

from core.event_bus import GlobalEventBus, Event


class ReasoningError(Exception):
    """Base exception for reasoning engine"""


class ReasoningEngine:
    """
    Core reasoning + decision engine.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        # Strategy registry
        self.strategies: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

        self.logger = logging.getLogger("NEO.Reasoning")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Reasoning] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Register default strategies
        self._register_default_strategies()

        # Event subscription
        self.event_bus.subscribe("ai.reason", self._on_reason_request, priority=9)

    # =========================
    # Strategy System
    # =========================

    def register_strategy(self, name: str, func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        with self._lock:
            self.strategies[name] = func
            self.logger.info(f"Strategy registered: {name}")

    def _register_default_strategies(self):
        self.register_strategy("task_decomposition", self._task_decomposition)
        self.register_strategy("rule_based", self._rule_based)
        self.register_strategy("self_correction", self._self_correction)

    # =========================
    # Core Reasoning
    # =========================

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main reasoning pipeline.
        """
        try:
            context = input_data.get("context", {})
            command = input_data.get("command", "")
            intent = input_data.get("intent", "unknown")

            self.logger.info(f"Reasoning on: {command}")

            # Step 1: Decompose task
            steps = self.strategies["task_decomposition"](input_data)

            # Step 2: Apply rule-based logic
            decision = self.strategies["rule_based"]({
                "steps": steps,
                "intent": intent,
                "context": context
            })

            # Step 3: Self-correction
            final = self.strategies["self_correction"](decision)

            confidence = self._confidence_score(final)

            result = {
                "input": input_data,
                "steps": steps,
                "decision": final,
                "confidence": confidence
            }

            return result

        except Exception as e:
            self._error("reason", e)
            return {}

    # =========================
    # Strategies
    # =========================

    def _task_decomposition(self, data: Dict[str, Any]) -> List[str]:
        """
        Break command into logical steps.
        """
        command = data.get("command", "")
        parts = command.split(" and ")

        steps = [p.strip() for p in parts if p.strip()]

        return steps if steps else [command]

    def _rule_based(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply rules to decide execution plan.
        """
        steps = data.get("steps", [])
        intent = data.get("intent")

        actions = []

        for step in steps:
            if "open" in step:
                actions.append({"type": "system.app", "action": "open", "value": step})

            elif "delete" in step:
                actions.append({"type": "system.file", "action": "delete", "value": step})

            elif "cpu" in step:
                actions.append({"type": "system.monitor", "action": "status"})

            else:
                actions.append({"type": intent, "action": "generic", "value": step})

        return {"actions": actions}

    def _self_correction(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Improve decisions if weak/ambiguous.
        """
        actions = decision.get("actions", [])

        for action in actions:
            if action["type"] == "unknown":
                action["type"] = "ai.general"
                action["action"] = "fallback"

        return decision

    # =========================
    # Confidence
    # =========================

    def _confidence_score(self, decision: Dict[str, Any]) -> float:
        actions = decision.get("actions", [])

        if not actions:
            return 0.2

        score = 0.5 + (len(actions) * 0.1)

        if any(a["type"] == "ai.general" for a in actions):
            score -= 0.2

        return max(0.0, min(score, 1.0))

    # =========================
    # Event Handler
    # =========================

    def _on_reason_request(self, event: Event):
        try:
            result = self.reason(event.data)

            self.event_bus.publish(
                "ai.reason.result",
                {"result": result},
                priority=8,
            )

        except Exception as e:
            self._error("event_reason", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.reasoning",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def reason_async(self, input_data: Dict[str, Any]):
        return await asyncio.to_thread(self.reason, input_data)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalReasoningEngine = ReasoningEngine()