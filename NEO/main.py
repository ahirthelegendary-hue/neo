"""
main.py

NEO AI OS - Main Entry Point

Responsibilities:
- Initialize all core systems
- Load modules and plugins
- Start background services (API, UI, Monitor, Scheduler, etc.)
- Wire EventBus with modules
- Boot sequence (Jarvis-style startup)

Features:
- Central orchestrator
- Safe startup sequence
- Module health check
- Graceful shutdown handling
- Logging integration

Run:
python main.py
"""

from __future__ import annotations

import asyncio
import json
import psutil
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import time
import threading
import logging
import traceback
import signal
import sys


# Core
from core.event_bus import GlobalEventBus
from core.module_loader import GlobalModuleLoader

# Systems
from system.system_monitor import GlobalSystemMonitor
from system.scheduler import GlobalScheduler
from system.process_manager import GlobalProcessManager

# AI
from ai.nlp import GlobalNLPProcessor
from ai.reasoning_engine import GlobalReasoningEngine
from ai.planner import GlobalPlanner

# Security
from security.firewall_manager import GlobalFirewallManager
from security.intrusion_detection import GlobalIDS
from security.encryption_manager import GlobalEncryptionManager

# Vision
from vision.object_detection import GlobalObjectDetector
from vision.face_recognition import GlobalFaceRecognition
from vision.ocr_reader import GlobalOCRReader

# DevOps
from devops.code_analyzer import GlobalCodeAnalyzer
from devops.git_manager import GlobalGitManager

# Automation
from automation.task_manager import GlobalTaskManager
from automation.workflow_engine import GlobalWorkflowEngine

# UI
from ui.desktop_overlay import GlobalDesktopOverlay
from ui.notification_manager import GlobalNotificationManager

# API
from api.rest_server import GlobalRestServer

# Data
from data.storage_manager import GlobalStorageManager

# Logs
from logs.logger import GlobalLogger

# Plugins
from plugins.plugin_manager import GlobalPluginManager

from security.intrusion_detection import GlobalIDS

class NEOSystem:
    """
    Main system controller.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self.running = False

        self.logger = logging.getLogger("NEO.Main")

    # =========================
    # Boot Sequence
    # =========================

    def boot(self):
        try:
            print("\n[NEO] Initializing System...\n")

            self._init_logging()
            self._init_modules()
            self._start_services()

            self.running = True

            print("\n[NEO] System Ready ✅\n")

            self._main_loop()

        except Exception as e:
            print("[FATAL] Boot failed:", e)
            traceback.print_exc()

    def _init_logging(self):
        GlobalLogger.info("Logging system initialized")

    def _init_modules(self):
        GlobalLogger.info("Loading modules...")

        # Load plugins
        GlobalPluginManager.discover()

        GlobalLogger.info("Modules loaded")

    def _start_services(self):
        GlobalLogger.info("Starting services...")

        # Core Systems
        GlobalScheduler._start(None)
        GlobalSystemMonitor._start(None)

        # Security
        GlobalIDS._start(None)

        # UI + Notifications
        GlobalNotificationManager.start()
        GlobalDesktopOverlay.start()

        # API Server
        GlobalRestServer.start()

        GlobalLogger.info("All services started")

    # =========================
    # Main Loop
    # =========================

    def _main_loop(self):
        while self.running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                self.shutdown()

    # =========================
    # Shutdown
    # =========================

    def shutdown(self):
        print("\n[NEO] Shutting down...\n")

        try:
            self.running = False

            # Stop services
            GlobalSystemMonitor._stop(None)
            GlobalScheduler._stop(None)
            GlobalIDS._stop(None)
            GlobalNotificationManager.stop()

            print("[NEO] Shutdown complete.")

            sys.exit(0)

        except Exception as e:
            print("[ERROR] Shutdown error:", e)


# =========================
# Signal Handling
# =========================

def handle_signal(sig, frame):
    system.shutdown()


# =========================
# Entry
# =========================

if __name__ == "__main__":
    system = NEOSystem()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    #system.boot()


clients = []

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

# CORS (React ke liye)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    print(f"NEW CLIENT CONNECTED: {len(clients)}")

    try:
        while True:
            data = await websocket.receive_text()
            print("RECEIVED:", data)

            # reply bhej
            await websocket.send_text(f"NEO RESPONSE: {data}")

    except Exception as e:
        print("ERROR:", e)

    finally:
        if websocket in clients:
            clients.remove(websocket)
        print("CLIENT DISCONNECTED")

# Ye function har 2 second mein "System Active" ka signal bhejega
async def send_logs():
    while True:
        for client in clients:
            try:
                await client.send_text(f"⚡ NEO System Pulse: STABLE | Clients: {len(clients)}")
            except:
                pass
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    print("🚀 NEO BACKEND STARTED")
    asyncio.create_task(send_logs())

from fastapi.middleware.cors import CORSMiddleware

# ... app = FastAPI() ke baad ...
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Sabhi origins allow karne ke liye
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import psutil

async def send_logs():
    while True:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        clients_count = len(clients)

        data = {
            "type": "system",
            "cpu": cpu,
            "ram": ram,
            "clients": clients_count
        }

        for client in clients.copy():
            try:
                await client.send_text(json.dumps(data))   # ✅ FIXED
            except:
                clients.remove(client)

        await asyncio.sleep(2)