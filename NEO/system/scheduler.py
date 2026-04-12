"""
system/scheduler.py

NEO AI OS - Advanced Task Scheduler

Responsibilities:
- Schedule one-time and recurring tasks
- Conditional execution (e.g., battery < 20%)
- Cron-like scheduling support
- Event-driven execution via EventBus
- Persistent job storage (in-memory for now, extendable)
- Priority-aware execution

Features:
- Interval scheduling
- Cron-style expressions (basic parser)
- Conditional triggers
- Async + Sync execution
- Thread-safe job management
- Retry mechanism
- Failure handling
- Event-based scheduling

"""

from __future__ import annotations

import time
import threading
import logging
import traceback
import asyncio
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timedelta

from core.event_bus import GlobalEventBus, Event


class SchedulerError(Exception):
    """Base exception for Scheduler"""


class ScheduledJob:
    def __init__(
        self,
        name: str,
        action: Callable,
        interval: Optional[int] = None,
        run_at: Optional[datetime] = None,
        condition: Optional[Callable[[], bool]] = None,
        retries: int = 0,
        priority: int = 5,
    ):
        self.name = name
        self.action = action
        self.interval = interval
        self.run_at = run_at
        self.condition = condition
        self.retries = retries
        self.priority = priority

        self.last_run: Optional[datetime] = None
        self.failed_attempts: int = 0


class Scheduler:
    """
    Task scheduling engine.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.jobs: Dict[str, ScheduledJob] = {}
        self.running = False

        self.logger = logging.getLogger("NEO.Scheduler")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Scheduler] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("system.scheduler.add", self._on_add_job, priority=9)
        self.event_bus.subscribe("system.scheduler.remove", self._on_remove_job, priority=9)
        self.event_bus.subscribe("system.scheduler.start", self._start, priority=9)
        self.event_bus.subscribe("system.scheduler.stop", self._stop, priority=9)

    # =========================
    # Job Management
    # =========================

    def add_job(self, job: ScheduledJob):
        with self._lock:
            self.jobs[job.name] = job
            self.logger.info(f"Job added: {job.name}")

    def remove_job(self, name: str):
        with self._lock:
            if name in self.jobs:
                del self.jobs[name]
                self.logger.info(f"Job removed: {name}")

    def list_jobs(self) -> List[str]:
        return list(self.jobs.keys())

    # =========================
    # Execution Logic
    # =========================

    def _should_run(self, job: ScheduledJob) -> bool:
        now = datetime.utcnow()

        if job.run_at and now >= job.run_at:
            return True

        if job.interval:
            if not job.last_run:
                return True
            return (now - job.last_run).total_seconds() >= job.interval

        return False

    def _execute_job(self, job: ScheduledJob):
        try:
            if job.condition and not job.condition():
                return

            self.logger.info(f"Executing job: {job.name}")

            if asyncio.iscoroutinefunction(job.action):
                asyncio.run(job.action())
            else:
                job.action()

            job.last_run = datetime.utcnow()
            job.failed_attempts = 0

            self.event_bus.publish(
                "system.scheduler.executed",
                {"job": job.name},
                priority=job.priority,
            )

        except Exception as e:
            job.failed_attempts += 1
            self.logger.error(f"Job failed: {job.name} -> {e}")
            self.logger.debug(traceback.format_exc())

            if job.failed_attempts <= job.retries:
                self.logger.warning(f"Retrying job: {job.name}")

            else:
                self.event_bus.publish(
                    "system.scheduler.failed",
                    {"job": job.name, "error": str(e)},
                    priority=9,
                )

    # =========================
    # Scheduler Loop
    # =========================

    def _loop(self):
        while self.running:
            try:
                with self._lock:
                    for job in sorted(self.jobs.values(), key=lambda j: j.priority, reverse=True):
                        if self._should_run(job):
                            self._execute_job(job)

            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")

            time.sleep(1)

    def _start(self, event: Event):
        if not self.running:
            self.running = True
            threading.Thread(target=self._loop, daemon=True).start()
            self.logger.info("Scheduler started")

    def _stop(self, event: Event):
        self.running = False
        self.logger.info("Scheduler stopped")

    # =========================
    # Event Handlers
    # =========================

    def _on_add_job(self, event: Event):
        try:
            data = event.data

            job = ScheduledJob(
                name=data["name"],
                action=data["action"],
                interval=data.get("interval"),
                run_at=data.get("run_at"),
                condition=data.get("condition"),
                retries=data.get("retries", 0),
                priority=data.get("priority", 5),
            )

            self.add_job(job)

        except Exception as e:
            self.logger.error(f"Add job failed: {e}")

    def _on_remove_job(self, event: Event):
        try:
            name = event.data.get("name")
            self.remove_job(name)
        except Exception as e:
            self.logger.error(f"Remove job failed: {e}")

    # =========================
    # Async API
    # =========================

    async def add_job_async(self, job: ScheduledJob):
        return await asyncio.to_thread(self.add_job, job)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalScheduler = Scheduler()