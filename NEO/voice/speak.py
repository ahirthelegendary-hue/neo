"""
voice/speak.py

NEO AI OS - Voice Output Engine

Responsibilities:
- Convert text to speech (TTS)
- Manage speech queue
- Support interrupt / stop speaking
- Async + thread-safe speaking
- Emit events for speech lifecycle

Features:
- Queue-based speech system
- Interrupt support
- Configurable voice properties
- Event-driven integration
- Error-safe execution

Dependencies:
pip install pyttsx3
"""

from __future__ import annotations

import threading
import queue
import logging
import traceback
import time
from typing import Optional

import pyttsx3

from core.event_bus import GlobalEventBus, Event


class VoiceSpeakError(Exception):
    """Voice speak error"""


class VoiceSpeaker:
    """
    Text-to-Speech Engine
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self.engine = pyttsx3.init()

        self.queue: queue.Queue[str] = queue.Queue()
        self.running = True
        self.speaking = False

        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.VoiceSpeaker")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [VoiceSpeak] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._configure_engine()
        self._start_worker()

        # Subscribe events
        self.event_bus.subscribe("voice.speak", self._on_speak, priority=9)
        self.event_bus.subscribe("voice.stop", self._on_stop, priority=9)

    # =========================
    # Engine Setup
    # =========================

    def _configure_engine(self):
        try:
            self.engine.setProperty("rate", 180)
            self.engine.setProperty("volume", 1.0)

            voices = self.engine.getProperty("voices")
            if voices:
                self.engine.setProperty("voice", voices[0].id)

            self.logger.info("TTS engine configured")

        except Exception as e:
            self.logger.error(f"Engine config failed: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Worker Thread
    # =========================

    def _start_worker(self):
        thread = threading.Thread(target=self._worker_loop, daemon=True)
        thread.start()

    def _worker_loop(self):
        while self.running:
            try:
                text = self.queue.get(timeout=0.5)

                with self._lock:
                    self.speaking = True

                self.event_bus.publish("voice.started", {"text": text}, priority=7)

                self.logger.info(f"Speaking: {text}")

                self.engine.say(text)
                self.engine.runAndWait()

                self.event_bus.publish("voice.finished", {"text": text}, priority=7)

                with self._lock:
                    self.speaking = False

            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Speech error: {e}")
                self.logger.debug(traceback.format_exc())
                self.event_bus.publish("voice.error", {"error": str(e)}, priority=9)

            time.sleep(0.05)

    # =========================
    # Event Handlers
    # =========================

    def _on_speak(self, event: Event):
        try:
            text = event.data.get("text")

            if not text:
                self.logger.warning("Empty text for speaking")
                return

            self.queue.put(text)

        except Exception as e:
            self.logger.error(f"Speak event failed: {e}")

    def _on_stop(self, event: Event):
        try:
            with self._lock:
                if self.speaking:
                    self.engine.stop()
                    self._clear_queue()
                    self.speaking = False

            self.logger.info("Speech stopped")

        except Exception as e:
            self.logger.error(f"Stop failed: {e}")

    # =========================
    # Queue Control
    # =========================

    def _clear_queue(self):
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

    # =========================
    # Public API
    # =========================

    def speak(self, text: str):
        self.queue.put(text)

    def stop(self):
        self._on_stop(Event("voice.stop", {}))

    def shutdown(self):
        self.running = False
        self.stop()
        self.logger.warning("VoiceSpeaker shutdown")


# =========================
# GLOBAL INSTANCE
# =========================

GlobalVoiceSpeaker = VoiceSpeaker()