"""
voice/__init__.py

NEO AI OS - Voice Module Manager

Responsibilities:
- Initialize and manage voice subsystems
- Integrate Speech-to-Text (STT) and Text-to-Speech (TTS)
- Handle lifecycle (start/stop)
- Track voice metrics (commands, responses, errors)
- EventBus integration

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event
from .listen import GlobalSpeechToText
from .speak import GlobalTextToSpeech

class VoiceError(Exception):
    pass


class VoiceManager:
    def __init__(self):
        self.event_bus = GlobalEventBus

        self.stt = GlobalSpeechToText
        self.tts = GlobalTextToSpeech

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.commands_processed: int = 0
        self.responses_spoken: int = 0
        self.errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.Voice.Manager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Voice.Manager] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._subscribe_events()

    # =========================
    # Lifecycle
    # =========================

    def start(self) -> bool:
        with self._lock:
            try:
                if self._running:
                    return False

                self.start_time = time.time()
                self._running = True

                self.logger.info("Voice Manager started")
                return True

            except Exception as e:
                self._error("start", e)
                return False

    def stop(self) -> bool:
        with self._lock:
            try:
                if not self._running:
                    return False

                self._running = False
                self.logger.info("Voice Manager stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics
    # =========================

    def _inc_command(self):
        with self._lock:
            self.commands_processed += 1

    def _inc_response(self):
        with self._lock:
            self.responses_spoken += 1

    def _inc_error(self):
        with self._lock:
            self.errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            return {
                "status": "running" if self._running else "stopped",
                "uptime": round(uptime, 2),
                "commands_processed": self.commands_processed,
                "responses_spoken": self.responses_spoken,
                "errors": self.errors,
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("voice.command", self._on_command, priority=9)
            self.event_bus.subscribe("voice.speak", self._on_speak, priority=9)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_command(self, event: Event):
        try:
            self._inc_command()
        except Exception as e:
            self._error("command_event", e)

    def _on_speak(self, event: Event):
        try:
            self._inc_response()
        except Exception as e:
            self._error("speak_event", e)

    def _on_shutdown(self, event: Event):
        try:
            self.stop()
        except Exception as e:
            self._error("shutdown_event", e)

    # =========================
    # Error Handling
    # =========================

    def _error(self, source: str, error: Exception):
        self._inc_error()

        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.voice_manager",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalVoiceManager = VoiceManager()