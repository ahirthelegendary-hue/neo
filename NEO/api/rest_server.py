"""
api/rest_server.py

NEO AI OS - REST API Server

Responsibilities:
- Expose NEO functionalities via HTTP API
- Accept commands and route them into EventBus
- Provide system status endpoints
- Secure endpoints (basic token auth)
- JSON-based request/response handling

Features:
- Built using FastAPI
- Async endpoints
- Event-driven execution
- Token-based authentication
- Health check & metrics endpoints
- Thread-safe integration

Dependencies:
pip install fastapi uvicorn
"""

from __future__ import annotations

import threading
import logging
import traceback
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
import uvicorn

from core.event_bus import GlobalEventBus


class APIServerError(Exception):
    """API server exception"""


class RestServer:
    """
    REST API server for NEO.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000, token: str = "neo_secure"):
        self.event_bus = GlobalEventBus
        self.host = host
        self.port = port
        self.token = token

        self.app = FastAPI(title="NEO AI OS API")

        self.logger = logging.getLogger("NEO.API")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [API] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._setup_routes()

    # =========================
    # Auth
    # =========================

    def _verify_token(self, authorization: Optional[str]):
        if authorization != f"Bearer {self.token}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    # =========================
    # Routes
    # =========================

    def _setup_routes(self):

        @self.app.get("/")
        async def root():
            return {"status": "NEO API Running"}

        @self.app.get("/health")
        async def health():
            return {"status": "ok"}

        @self.app.post("/command")
        async def send_command(payload: Dict[str, Any], authorization: Optional[str] = Header(None)):
            try:
                self._verify_token(authorization)

                command = payload.get("command")

                self.event_bus.publish(
                    "command.received",
                    {"command": command},
                    priority=10,
                )

                return {"status": "command dispatched"}

            except Exception as e:
                self._error("command", e)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/event")
        async def publish_event(payload: Dict[str, Any], authorization: Optional[str] = Header(None)):
            try:
                self._verify_token(authorization)

                name = payload.get("name")
                data = payload.get("data", {})

                self.event_bus.publish(name, data, priority=7)

                return {"status": "event published"}

            except Exception as e:
                self._error("event", e)
                raise HTTPException(status_code=500, detail=str(e))

    # =========================
    # Run Server
    # =========================

    def start(self):
        try:
            threading.Thread(
                target=lambda: uvicorn.run(self.app, host=self.host, port=self.port),
                daemon=True,
            ).start()

            self.logger.info(f"API server started on {self.host}:{self.port}")

        except Exception as e:
            self._error("start", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.api",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalRestServer = RestServer()