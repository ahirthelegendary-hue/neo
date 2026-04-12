"""
core/event_bus.py

NEO AI OS - Advanced Event Bus (Nervous System)

This module provides a production-grade, high-performance, fully asynchronous,
thread-safe, middleware-enabled, wildcard-capable Event Bus.

Key Features:
- Sync + Async subscriber support (asyncio integrated)
- Wildcard subscriptions (e.g., system.*, vision.face.*)
- Middleware pipeline (pre-processing hooks)
- Event TTL (time-to-live) and Priority (0–9 levels)
- Thread safety (RLock + Semaphore)
- Error isolation (no crash propagation)
- Execution analytics (timing, failures, frequency)
- Subscriber timeouts
- Global singleton bus
- Deep logging & observability

Author: NEO Core System
"""

from __future__ import annotations

import asyncio
import threading
import logging
import traceback
import time
import fnmatch
from typing import Any, Callable, Dict, List, Optional, Union, Coroutine
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta


# =========================
# Custom Exceptions
# =========================

class EventBusError(Exception):
    """Base exception for EventBus"""


class SubscriberTimeout(EventBusError):
    """Raised when a subscriber exceeds allowed execution time"""


class MiddlewareError(EventBusError):
    """Raised when middleware fails"""


# =========================
# Event Model
# =========================

@dataclass
class Event:
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 0 (lowest) - 9 (highest)
    ttl: Optional[float] = None  # seconds
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl)


# =========================
# Subscriber Model
# =========================

@dataclass
class Subscriber:
    callback: Callable[[Event], Union[None, Coroutine]]
    is_async: bool
    priority: int
    timeout: float = 5.0


# =========================
# Analytics Engine
# =========================

class EventAnalytics:
    def __init__(self):
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.failures: Dict[str, int] = defaultdict(int)
        self.execution_times: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.RLock()

    def record_event(self, name: str):
        with self.lock:
            self.event_counts[name] += 1

    def record_failure(self, name: str):
        with self.lock:
            self.failures[name] += 1

    def record_execution_time(self, name: str, duration: float):
        with self.lock:
            self.execution_times[name].append(duration)

    def summary(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "events": dict(self.event_counts),
                "failures": dict(self.failures),
                "avg_time": {
                    k: (sum(v) / len(v) if v else 0)
                    for k, v in self.execution_times.items()
                },
            }


# =========================
# Event Bus Core
# =========================

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Subscriber]] = defaultdict(list)
        self._middlewares: List[Callable[[Event], Event]] = []
        self._lock = threading.RLock()
        self._semaphore = threading.Semaphore(100)
        self._analytics = EventAnalytics()

        self.logger = logging.getLogger("NEO.EventBus")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [EventBus] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    # =========================
    # Subscription
    # =========================

    def subscribe(
        self,
        event_pattern: str,
        callback: Callable[[Event], Union[None, Coroutine]],
        priority: int = 5,
        timeout: float = 5.0,
    ):
        with self._lock:
            sub = Subscriber(
                callback=callback,
                is_async=asyncio.iscoroutinefunction(callback),
                priority=priority,
                timeout=timeout,
            )
            self._subscribers[event_pattern].append(sub)
            self._subscribers[event_pattern].sort(
                key=lambda s: s.priority, reverse=True
            )

        self.logger.debug(f"Subscribed to pattern: {event_pattern}")

    def unsubscribe(self, event_pattern: str, callback: Callable):
        with self._lock:
            if event_pattern in self._subscribers:
                self._subscribers[event_pattern] = [
                    s for s in self._subscribers[event_pattern]
                    if s.callback != callback
                ]

    # =========================
    # Middleware
    # =========================

    def add_middleware(self, middleware: Callable[[Event], Event]):
        with self._lock:
            self._middlewares.append(middleware)
        self.logger.debug("Middleware added")

    def _apply_middlewares(self, event: Event) -> Event:
        for middleware in self._middlewares:
            try:
                event = middleware(event)
            except Exception as e:
                self.logger.error(f"Middleware error: {e}")
                self.logger.debug(traceback.format_exc())
                raise MiddlewareError(str(e))
        return event

    # =========================
    # Matching Logic
    # =========================

    def _match_subscribers(self, event_name: str) -> List[Subscriber]:
        matched = []
        with self._lock:
            for pattern, subs in self._subscribers.items():
                if fnmatch.fnmatch(event_name, pattern):
                    matched.extend(subs)
        return sorted(matched, key=lambda s: s.priority, reverse=True)

    # =========================
    # Publish (Sync)
    # =========================

    def publish(self, name: str, data: Optional[Dict[str, Any]] = None,
                priority: int = 5, ttl: Optional[float] = None):

        event = Event(name=name, data=data or {}, priority=priority, ttl=ttl)

        if event.is_expired():
            self.logger.warning(f"Event expired: {name}")
            return

        self._analytics.record_event(name)

        try:
            event = self._apply_middlewares(event)
        except MiddlewareError:
            return

        subscribers = self._match_subscribers(name)

        for sub in subscribers:
            self._execute_subscriber(sub, event)

    # =========================
    # Publish (Async)
    # =========================

    async def publish_async(self, name: str, data=None,
                            priority=5, ttl=None):

        event = Event(name=name, data=data or {}, priority=priority, ttl=ttl)

        if event.is_expired():
            return

        self._analytics.record_event(name)

        try:
            event = self._apply_middlewares(event)
        except MiddlewareError:
            return

        subscribers = self._match_subscribers(name)

        tasks = [
            self._execute_subscriber_async(sub, event)
            for sub in subscribers
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    # =========================
    # Execution Handlers
    # =========================

    def _execute_subscriber(self, sub: Subscriber, event: Event):
        with self._semaphore:
            start = time.time()
            try:
                if sub.is_async:
                    asyncio.run(self._execute_subscriber_async(sub, event))
                else:
                    sub.callback(event)
            except Exception as e:
                self.logger.error(f"Subscriber error: {e}")
                self.logger.debug(traceback.format_exc())
                self._analytics.record_failure(event.name)
            finally:
                duration = time.time() - start
                self._analytics.record_execution_time(event.name, duration)

    async def _execute_subscriber_async(self, sub: Subscriber, event: Event):
        start = time.time()
        try:
            await asyncio.wait_for(sub.callback(event), timeout=sub.timeout)
        except asyncio.TimeoutError:
            self.logger.error("Subscriber timeout")
            self._analytics.record_failure(event.name)
            raise SubscriberTimeout()
        except Exception as e:
            self.logger.error(f"Async subscriber error: {e}")
            self.logger.debug(traceback.format_exc())
            self._analytics.record_failure(event.name)
        finally:
            duration = time.time() - start
            self._analytics.record_execution_time(event.name, duration)

    # =========================
    # Utilities
    # =========================

    def clear(self):
        with self._lock:
            self._subscribers.clear()
            self._middlewares.clear()

    def analytics(self) -> Dict[str, Any]:
        return self._analytics.summary()


# =========================
# GLOBAL SINGLETON
# =========================

GlobalEventBus = EventBus()