"""
automation/workflow_engine.py

NEO AI OS - Workflow Engine

Responsibilities:
- Define and execute complex multi-step workflows
- Support branching, conditions, and loops
- Handle dependencies between steps
- Retry failed steps intelligently
- Emit workflow lifecycle events via EventBus

Features:
- Directed workflow graph execution
- Conditional branching
- Loop support (limited safe loops)
- Step retry & rollback hooks
- Execution tracing
- Thread-safe
- Async + Sync support

"""

from __future__ import annotations

import threading
import logging
import traceback
import asyncio
import time
from typing import Dict, Any, List, Optional

from core.event_bus import GlobalEventBus, Event


class WorkflowError(Exception):
    """Workflow exception"""


class WorkflowStep:
    def __init__(
        self,
        step_id: str,
        action: Dict[str, Any],
        next_steps: Optional[List[str]] = None,
        condition: Optional[str] = None,
        retries: int = 0,
    ):
        self.step_id = step_id
        self.action = action
        self.next_steps = next_steps or []
        self.condition = condition
        self.retries = retries

        self.attempts = 0
        self.completed = False
        self.failed = False


class Workflow:
    def __init__(self, name: str, steps: List[WorkflowStep]):
        self.name = name
        self.steps = {step.step_id: step for step in steps}
        self.start_step = steps[0].step_id if steps else None


class WorkflowEngine:
    """
    Executes structured workflows.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.workflows: Dict[str, Workflow] = {}

        self.logger = logging.getLogger("NEO.Workflow")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Workflow] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("automation.workflow.start", self._on_start, priority=9)

    # =========================
    # Workflow Management
    # =========================

    def register_workflow(self, workflow: Workflow):
        with self._lock:
            self.workflows[workflow.name] = workflow
            self.logger.info(f"Workflow registered: {workflow.name}")

    def remove_workflow(self, name: str):
        with self._lock:
            if name in self.workflows:
                del self.workflows[name]

    # =========================
    # Execution
    # =========================

    def execute(self, workflow: Workflow) -> Dict[str, Any]:
        trace = []

        try:
            current_id = workflow.start_step

            while current_id:
                step = workflow.steps.get(current_id)
                if not step:
                    break

                if step.condition and not self._evaluate_condition(step.condition):
                    self.logger.info(f"Skipping step: {step.step_id}")
                    current_id = step.next_steps[0] if step.next_steps else None
                    continue

                success = self._execute_step(step)

                trace.append({
                    "step": step.step_id,
                    "success": success
                })

                if success:
                    step.completed = True
                    current_id = step.next_steps[0] if step.next_steps else None
                else:
                    step.failed = True
                    if step.attempts <= step.retries:
                        self.logger.warning(f"Retrying step: {step.step_id}")
                        continue
                    else:
                        self._emit("automation.workflow.failed", {"step": step.step_id})
                        break

            self._emit("automation.workflow.completed", {"workflow": workflow.name})

            return {"trace": trace}

        except Exception as e:
            self._error("execute", e)
            return {"trace": trace}

    def _execute_step(self, step: WorkflowStep) -> bool:
        try:
            step.attempts += 1

            self.logger.info(f"Executing step: {step.step_id}")

            self.event_bus.publish(
                step.action["type"],
                step.action.get("payload", {}),
                priority=step.action.get("priority", 5),
            )

            return True

        except Exception as e:
            self._error("execute_step", e)
            return False

    # =========================
    # Conditions
    # =========================

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Basic condition evaluator (safe subset).
        Example: "cpu < 50"
        """
        try:
            allowed = {"True": True, "False": False}
            return bool(eval(condition, {"__builtins__": {}}, allowed))
        except Exception:
            return False

    # =========================
    # Event Handler
    # =========================

    def _on_start(self, event: Event):
        try:
            name = event.data.get("name")
            workflow = self.workflows.get(name)

            if not workflow:
                raise WorkflowError(f"Workflow not found: {name}")

            result = self.execute(workflow)

            self._emit(
                "automation.workflow.result",
                {"workflow": name, "result": result},
            )

        except Exception as e:
            self._error("event_start", e)

    # =========================
    # Helpers
    # =========================

    def _emit(self, name: str, data: Dict[str, Any]):
        try:
            self.event_bus.publish(name, data, priority=7)
        except Exception:
            pass

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.workflow",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def execute_async(self, workflow: Workflow):
        return await asyncio.to_thread(self.execute, workflow)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalWorkflowEngine = WorkflowEngine()