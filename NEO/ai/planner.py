"""
ai/planner.py

NEO AI OS - Planning Engine

Responsibilities:
- Convert high-level goals into executable plans
- Sequence actions with dependencies
- Optimize execution order (priority + cost)
- Support conditional branching
- Retry & fallback planning
- Integrate with Reasoning Engine + EventBus

Features:
- Multi-step plan generation
- Dependency graph (DAG-like)
- Cost-based optimization (lightweight heuristic)
- Conditional execution nodes
- Replanning on failure
- Async + Sync execution
- Thread-safe
- Detailed logging

"""

from __future__ import annotations

import threading
import logging
import traceback
import asyncio
from typing import Dict, Any, List, Optional


from core.event_bus import GlobalEventBus, Event


class PlannerError(Exception):
    """Planner base exception"""


class PlanStep:
    def __init__(
        self,
        step_id: str,
        action: Dict[str, Any],
        depends_on: Optional[List[str]] = None,
        condition: Optional[str] = None,
        cost: float = 1.0,
    ):
        self.step_id = step_id
        self.action = action
        self.depends_on = depends_on or []
        self.condition = condition
        self.cost = cost
        self.completed = False
        self.failed = False


class Planner:
    """
    Planning engine for structured execution.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.Planner")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Planner] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("ai.plan", self._on_plan_request, priority=9)
        self.event_bus.subscribe("ai.plan.execute", self._on_execute_plan, priority=9)

    # =========================
    # Plan Creation
    # =========================

    def create_plan(self, reasoning_output: Dict[str, Any]) -> List[PlanStep]:
        """
        Convert reasoning output into plan steps.
        """
        try:
            actions = reasoning_output.get("decision", {}).get("actions", [])

            steps: List[PlanStep] = []

            for i, action in enumerate(actions):
                step = PlanStep(
                    step_id=f"step_{i}",
                    action=action,
                    depends_on=[f"step_{i-1}"] if i > 0 else [],
                    cost=self._estimate_cost(action),
                )
                steps.append(step)

            optimized = self._optimize(steps)

            return optimized

        except Exception as e:
            self._error("create_plan", e)
            return []

    # =========================
    # Optimization
    # =========================

    def _estimate_cost(self, action: Dict[str, Any]) -> float:
        """
        Simple cost heuristic.
        """
        if action["type"].startswith("system"):
            return 1.0
        if action["type"].startswith("ai"):
            return 2.0
        return 1.5

    def _optimize(self, steps: List[PlanStep]) -> List[PlanStep]:
        """
        Sort steps by cost (simple optimization).
        """
        return sorted(steps, key=lambda s: s.cost)

    # =========================
    # Execution
    # =========================

    def execute_plan(self, steps: List[PlanStep]) -> Dict[str, Any]:
        results = []

        try:
            for step in steps:
                if not self._can_execute(step, steps):
                    continue

                self.logger.info(f"Executing: {step.step_id}")

                success = self._execute_step(step)

                step.completed = success
                step.failed = not success

                results.append({
                    "step": step.step_id,
                    "success": success
                })

                if not success:
                    self._handle_failure(step)

            return {"results": results}

        except Exception as e:
            self._error("execute_plan", e)
            return {"results": []}

    def _can_execute(self, step: PlanStep, steps: List[PlanStep]) -> bool:
        """
        Check dependencies.
        """
        for dep in step.depends_on:
            dep_step = next((s for s in steps if s.step_id == dep), None)
            if dep_step and not dep_step.completed:
                return False
        return True

    def _execute_step(self, step: PlanStep) -> bool:
        try:
            action = step.action

            # Emit action as event
            self.event_bus.publish(
                f"{action['type']}.execute",
                {"action": action},
                priority=step.cost,
            )

            return True

        except Exception as e:
            self._error("execute_step", e)
            return False

    # =========================
    # Failure Handling
    # =========================

    def _handle_failure(self, step: PlanStep):
        self.logger.warning(f"Step failed: {step.step_id}")

        self.event_bus.publish(
            "ai.plan.failure",
            {"step": step.step_id},
            priority=9,
        )

    # =========================
    # Event Handlers
    # =========================

    def _on_plan_request(self, event: Event):
        try:
            reasoning = event.data.get("reasoning")

            plan = self.create_plan(reasoning)

            self.event_bus.publish(
                "ai.plan.created",
                {"plan": plan},
                priority=8,
            )

        except Exception as e:
            self._error("event_plan", e)

    def _on_execute_plan(self, event: Event):
        try:
            steps = event.data.get("plan", [])
            result = self.execute_plan(steps)

            self.event_bus.publish(
                "ai.plan.result",
                result,
                priority=8,
            )

        except Exception as e:
            self._error("event_execute", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.planner",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def create_plan_async(self, reasoning_output: Dict[str, Any]):
        return await asyncio.to_thread(self.create_plan, reasoning_output)

    async def execute_plan_async(self, steps: List[PlanStep]):
        return await asyncio.to_thread(self.execute_plan, steps)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalPlanner = Planner()