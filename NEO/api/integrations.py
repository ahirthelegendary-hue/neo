"""
api/integrations.py

NEO AI OS - API Integrations Layer

Responsibilities:
- Bridge REST API layer with internal EventBus
- Provide decorators and helpers for request tracking
- Normalize inbound/outbound API payloads
- Handle cross-module integrations (UI, AI, System, DevOps)
- Maintain integration metrics & error tracking

Features:
- Thread-safe metrics
- Request/response normalization
- Event-driven routing
- Decorators for FastAPI endpoints
- Broadcast utilities
- Health snapshot aggregation

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any, Callable, Awaitable, Optional
from functools import wraps

from core.event_bus import GlobalEventBus, Event
from api.__init__ import GlobalAPIManager


class APIIntegrationError(Exception):
    """API Integration exception"""
    pass


class APIIntegrations:
    """
    Integration layer between REST API and internal systems.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self.api_manager = GlobalAPIManager

        self._lock = threading.RLock()

        # Metrics
        self.route_hits: Dict[str, int] = {}
        self.last_request_ts: float = 0.0

        # Logger
        self.logger = logging.getLogger("NEO.API.Integrations")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [API.Integrations] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self._subscribe_events()

    # =========================
    # Decorators
    # =========================

    def track_request(self, route: str) -> Callable:
        """
        Decorator to track API requests.
        """

        def decorator(func: Callable[..., Awaitable]):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    self._record_hit(route)
                    self.api_manager.record_request()

                    response = await func(*args, **kwargs)

                    duration = time.time() - start
                    self._emit(
                        "api.request.completed",
                        {"route": route, "duration": duration},
                    )

                    return response

                except Exception as e:
                    self.api_manager.record_error()
                    self._error("track_request", e)
                    raise

            return wrapper

        return decorator

    # =========================
    # Normalization
    # =========================

    def normalize_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return {
                "data": payload.get("data", payload),
                "timestamp": time.time(),
                "source": "api",
            }
        except Exception as e:
            self._error("normalize_request", e)
            return payload

    def normalize_response(self, data: Any, success: bool = True) -> Dict[str, Any]:
        try:
            return {
                "success": success,
                "data": data,
                "timestamp": time.time(),
            }
        except Exception as e:
            self._error("normalize_response", e)
            return {"success": False, "error": str(e)}

    # =========================
    # Event Bridge
    # =========================

    def dispatch_event(self, name: str, payload: Dict[str, Any], priority: int = 7):
        try:
            normalized = self.normalize_request(payload)

            self.event_bus.publish(name, normalized, priority=priority)

        except Exception as e:
            self._error("dispatch_event", e)

    def broadcast(self, message: str):
        try:
            self.event_bus.publish(
                "api.broadcast",
                {"message": message},
                priority=8,
            )
        except Exception as e:
            self._error("broadcast", e)

    # =========================
    # Metrics
    # =========================

    def _record_hit(self, route: str):
        with self._lock:
            self.route_hits[route] = self.route_hits.get(route, 0) + 1
            self.last_request_ts = time.time()

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "routes": self.route_hits,
                "last_request": self.last_request_ts,
            }

    # =========================
    # Health Snapshot
    # =========================

    def get_health_snapshot(self) -> Dict[str, Any]:
        try:
            api_metrics = self.api_manager.get_metrics()
            integration_metrics = self.get_metrics()

            return {
                "api": api_metrics,
                "integrations": integration_metrics,
            }

        except Exception as e:
            self._error("health_snapshot", e)
            return {}

    # =========================
    # Event Subscriptions
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("api.request.completed", self._on_request_complete, priority=5)
        except Exception as e:
            self._error("subscribe_events", e)

    def _on_request_complete(self, event: Event):
        try:
            route = event.data.get("route")
            duration = event.data.get("duration")

            self.logger.debug(f"Request completed: {route} ({duration:.4f}s)")

        except Exception as e:
            self._error("request_complete", e)

    # =========================
    # Helpers
    # =========================

    def _emit(self, name: str, data: Dict[str, Any]):
        try:
            self.event_bus.publish(name, data, priority=6)
        except Exception:
            pass

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.api_integrations",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalAPIIntegrations = APIIntegrations()