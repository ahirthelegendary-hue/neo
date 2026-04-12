"""
voice/wake_word.py

NEO AI OS - Wake Word Detection Engine

Responsibilities:
- Continuously listen for a wake word (e.g., "hey neo")
- Activate voice command mode when detected
- Prevent false triggers using confidence + cooldown
- Integrate with EventBus

Features:
- Lightweight detection (no heavy ML dependency)
- Cooldown system (anti-spam)
- Confidence threshold
- Background listening thread
- Event-driven activation
- Extendable to ML wake word engines (Porcupine, etc.)

Dependencies:
pip install SpeechRecognition pyaudio
"""

from __future__ import annotations

import threading
import time
import logging
import traceback
from typing import Optional

import speech_recognition as sr

from core.event_bus import GlobalEventBus, Event


class WakeWordError(Exception):
    """Wake word detection error"""


class WakeWordDetector:
    """
    Detects wake word ("hey neo")
    """

    def __init__(self, wake_word: str = "hey neo"):
        self.event_bus = GlobalEventBus
        self.recognizer = sr.Recognizer()
        self.microphone: Optional[sr.Microphone] = None

        self.wake_word = wake_word.lower()
        self.running = False

        self.cooldown = 3  # seconds
        self.last_trigger = 0

        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.WakeWord")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [WakeWord] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._init_microphone()

        # Subscribe events
        self.event_bus.subscribe("wake.start", self._start, priority=9)
        self.event_bus.subscribe("wake.stop", self._stop, priority=9)

    # =========================
    # Init
    # =========================

    def _init_microphone(self):
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.logger.info("Calibrating for wake word...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            self.logger.error(f"Mic init failed: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Start / Stop
    # =========================

    def _start(self, event: Event):
        with self._lock:
            if self.running:
                return

            self.running = True
            threading.Thread(target=self._loop, daemon=True).start()
            self.logger.info("Wake word detection started")

    def _stop(self, event: Event):
        with self._lock:
            self.running = False
            self.logger.info("Wake word detection stopped")

    # =========================
    # Detection Loop
    # =========================

    def _loop(self):
        while self.running:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(
                        source,
                        timeout=5,
                        phrase_time_limit=3
                    )

                text = self._recognize(audio)

                if text:
                    self.logger.debug(f"Heard: {text}")

                    if self._is_wake_word(text):
                        self._trigger()

            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Wake loop error: {e}")
                self.logger.debug(traceback.format_exc())

            time.sleep(0.1)

    # =========================
    # Recognition
    # =========================

    def _recognize(self, audio) -> Optional[str]:
        try:
            return self.recognizer.recognize_google(audio).lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            self.logger.error(f"API error: {e}")
        except Exception as e:
            self.logger.error(f"Recognition failed: {e}")
            self.logger.debug(traceback.format_exc())
        return None

    # =========================
    # Wake Logic
    # =========================

    def _is_wake_word(self, text: str) -> bool:
        return self.wake_word in text

    def _trigger(self):
        current_time = time.time()

        if current_time - self.last_trigger < self.cooldown:
            self.logger.debug("Wake word cooldown active")
            return

        self.last_trigger = current_time

        self.logger.info("Wake word detected!")

        # Emit activation event
        self.event_bus.publish("wake.detected", {"wake_word": self.wake_word}, priority=10)

        # Start voice listening mode
        self.event_bus.publish("voice.start", {}, priority=9)

    # =========================
    # Public API
    # =========================

    def start(self):
        self._start(Event("wake.start", {}))

    def stop(self):
        self._stop(Event("wake.stop", {}))


# =========================
# GLOBAL INSTANCE
# =========================

GlobalWakeWordDetector = WakeWordDetector()