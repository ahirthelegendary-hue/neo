"""
main.py

NEO AI OS - Entry Point

Responsibilities:
- Bootstraps entire NEO system
- Initializes core components (EventBus, Brain, Memory, Parser, ModuleLoader)
- Registers system-wide middleware
- Starts async event loop
- Handles graceful shutdown
- Emits boot sequence events

Features:
- Async + Sync startup
- Health checks
- Startup diagnostics
- Global error handling
- Clean shutdown signals
- Logging orchestration
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import traceback
from typing import Any

# Core imports
from core.event_bus import GlobalEventBus
from core.module_loader import GlobalModuleLoader
from core.brain import GlobalBrain
from core.memory import GlobalMemory
from core.command_parser import GlobalCommandParser


class NEOSystem:
    """
    Main system controller
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self.module_loader = GlobalModuleLoader
        self.brain = GlobalBrain
        self.memory = GlobalMemory
        self.parser = GlobalCommandParser

        self.running = False

        self.logger = logging.getLogger("NEO.Main")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [NEO] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    # =========================
    # Middleware Setup
    # =========================

    def _register_middlewares(self):
        """
        Register global middleware for event interception
        """

        def logging_middleware(event):
            self.logger.debug(f"[EVENT FLOW] {event.name} -> {event.data}")
            return event

        def safety_middleware(event):
            # Basic safeguard
            if not isinstance(event.data, dict):
                event.data = {"wrapped": event.data}
            return event

        self.event_bus.add_middleware(logging_middleware)
        self.event_bus.add_middleware(safety_middleware)

    # =========================
    # Boot Sequence
    # =========================

    async def boot(self):
        """
        Start NEO system
        """
        try:
            self.logger.info("🚀 Booting NEO AI OS...")

            self._register_middlewares()

            # Load modules (future expansion ready)
            self.module_loader.load_all(".")

            # Emit system start event
            await self.event_bus.publish_async(
                "system.start",
                {"status": "booting"},
                priority=9,
            )

            self.running = True

            self.logger.info("✅ NEO System Boot Complete")

        except Exception as e:
            self.logger.error(f"Boot failed: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Main Loop
    # =========================

    async def run(self):
        """
        Main runtime loop
        """
        await self.boot()

        try:
            while self.running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            self.logger.warning("Main loop cancelled")

    # =========================
    # Shutdown
    # =========================

    async def shutdown(self):
        """
        Graceful shutdown
        """
        self.logger.warning("🛑 Shutting down NEO...")

        try:
            await self.event_bus.publish_async(
                "system.shutdown",
                {"status": "stopping"},
                priority=9,
            )

            self.module_loader.shutdown_all()

            self.running = False

            self.logger.info("✅ Shutdown complete")

        except Exception as e:
            self.logger.error(f"Shutdown error: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Signal Handling
    # =========================

    def _handle_signal(self, sig: Any, frame: Any):
        """
        Handle OS signals (Ctrl+C)
        """
        self.logger.warning(f"Signal received: {sig}")
        asyncio.create_task(self.shutdown())


# =========================
# ENTRY POINT
# =========================

async def main():
    system = NEOSystem()

    # Setup signal handlers
    signal.signal(signal.SIGINT, system._handle_signal)
    signal.signal(signal.SIGTERM, system._handle_signal)

    await system.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[NEO] Force shutdown by user")
    except Exception as e:
        print(f"[NEO] Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)