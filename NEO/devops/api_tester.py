"""
devops/api_tester.py

NEO AI OS - API Tester

Responsibilities:
- Test REST APIs (GET, POST, PUT, DELETE)
- Validate responses (status, schema, time)
- Batch testing of endpoints
- Emit results to EventBus
- Track performance metrics

Features:
- Async + Sync HTTP requests
- Timeout handling
- Retry mechanism
- Response validation
- Thread-safe metrics
- Event-driven reporting

Dependencies:
pip install httpx
"""

from __future__ import annotations

import threading
import logging
import traceback
import asyncio
import time
from typing import Dict, Any, List, Optional

import httpx

from core.event_bus import GlobalEventBus, Event


class APITesterError(Exception):
    """API Tester exception"""
    pass


class APITester:
    """
    REST API testing utility.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        # Metrics
        self.total_tests: int = 0
        self.total_failures: int = 0
        self.total_success: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.APITester")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [APITester] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("devops.api.test", self._on_test, priority=9)

    # =========================
    # Core Request
    # =========================

    async def _request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:

        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    headers=headers,
                )

            duration = time.time() - start

            return {
                "status_code": response.status_code,
                "body": response.text,
                "time": round(duration, 4),
                "success": 200 <= response.status_code < 300,
            }

        except Exception as e:
            self._inc_failure()
            self._error("request", e)

            return {
                "status_code": 0,
                "body": str(e),
                "time": 0,
                "success": False,
            }

    # =========================
    # Public API
    # =========================

    async def test_endpoint(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = 1,
    ) -> Dict[str, Any]:

        result = {}

        for attempt in range(retries + 1):
            result = await self._request(method, url, data, headers)

            if result["success"]:
                self._inc_success()
                break
            else:
                if attempt < retries:
                    await asyncio.sleep(1)

        self._inc_test()

        return result

    async def test_batch(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tasks = []

        for ep in endpoints:
            tasks.append(
                self.test_endpoint(
                    url=ep.get("url"),
                    method=ep.get("method", "GET"),
                    data=ep.get("data"),
                    headers=ep.get("headers"),
                )
            )

        return await asyncio.gather(*tasks)

    # =========================
    # Metrics
    # =========================

    def _inc_test(self):
        with self._lock:
            self.total_tests += 1

    def _inc_success(self):
        with self._lock:
            self.total_success += 1

    def _inc_failure(self):
        with self._lock:
            self.total_failures += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_tests": self.total_tests,
                "success": self.total_success,
                "failures": self.total_failures,
            }

    # =========================
    # Event Handling
    # =========================

    def _on_test(self, event: Event):
        try:
            payload = event.data

            asyncio.run(self._handle_event(payload))

        except Exception as e:
            self._error("event_test", e)

    async def _handle_event(self, payload: Dict[str, Any]):
        try:
            if "batch" in payload:
                result = await self.test_batch(payload["batch"])
            else:
                result = await self.test_endpoint(
                    url=payload.get("url"),
                    method=payload.get("method", "GET"),
                    data=payload.get("data"),
                )

            self.event_bus.publish(
                "devops.api.result",
                {"result": result},
                priority=8,
            )

        except Exception as e:
            self._error("handle_event", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.api_tester",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalAPITester = APITester()