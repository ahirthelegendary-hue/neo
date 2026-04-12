"""
api/web_api.py

NEO AI OS - Web API Layer (FastAPI Routes)

Responsibilities:
- Define HTTP routes for external interaction
- Integrate with EventBus via APIIntegrations
- Track requests and performance
- Provide command execution, events, metrics, health

Features:
- Async FastAPI endpoints
- Request tracking decorator
- Token auth (via RestServer layer if needed)
- Unified response format
- Error-safe execution

"""

from __future__ import annotations

import logging
import traceback
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Header

from core.event_bus import GlobalEventBus
from api.integrations import GlobalAPIIntegrations


router = APIRouter()
event_bus = GlobalEventBus
integrations = GlobalAPIIntegrations


logger = logging.getLogger("NEO.API.Web")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [API.Web] %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# =========================
# ROOT
# =========================

@router.get("/")
@integrations.track_request("/")
async def root():
    return integrations.normalize_response({"message": "NEO API Active"})


# =========================
# HEALTH
# =========================

@router.get("/health")
@integrations.track_request("/health")
async def health():
    try:
        snapshot = integrations.get_health_snapshot()
        return integrations.normalize_response(snapshot)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# COMMAND
# =========================

@router.post("/command")
@integrations.track_request("/command")
async def command(payload: Dict[str, Any]):
    try:
        cmd = payload.get("command")

        integrations.dispatch_event(
            "command.received",
            {"command": cmd},
            priority=10,
        )

        return integrations.normalize_response({"status": "command sent"})

    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# EVENT
# =========================

@router.post("/event")
@integrations.track_request("/event")
async def publish_event(payload: Dict[str, Any]):
    try:
        name = payload.get("name")
        data = payload.get("data", {})

        integrations.dispatch_event(name, data)

        return integrations.normalize_response({"status": "event published"})

    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# BROADCAST
# =========================

@router.post("/broadcast")
@integrations.track_request("/broadcast")
async def broadcast(payload: Dict[str, Any]):
    try:
        msg = payload.get("message", "")
        integrations.broadcast(msg)

        return integrations.normalize_response({"status": "broadcast sent"})

    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# METRICS
# =========================

@router.get("/metrics")
@integrations.track_request("/metrics")
async def metrics():
    try:
        data = integrations.get_health_snapshot()
        return integrations.normalize_response(data)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# DEBUG: RAW EVENT TRIGGER
# =========================

@router.post("/debug/emit")
@integrations.track_request("/debug/emit")
async def debug_emit(payload: Dict[str, Any]):
    try:
        name = payload.get("name")
        data = payload.get("data", {})

        event_bus.publish(name, data, priority=5)

        return integrations.normalize_response({"status": "debug event emitted"})

    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))