"""
voice/listen.py

NEO AI OS - Voice Input Listener

Responsibilities:
- Capture audio from microphone
- Convert speech to text (Speech Recognition)
- Handle noise reduction
- Detect silence and end of speech
- Emit parsed text to EventBus

Features:
- Continuous listening mode
- Timeout handling
- Noise adjustment
- Error recovery
- Async + Thread-safe execution
- Event-driven integration

NOTE:
Uses `speech_recognition` library.
Install: pip install SpeechRecognition pyaudio
"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Optional

import speech_recognition as sr

from core.event_bus import GlobalEventBus, Event


class VoiceListenerError(Exception):
    """Voice Listener Exception"""


class VoiceListener:
    """
    Handles microphone input and speech recognition.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self.recognizer = sr.Recognizer()
        self.microphone: Optional[sr.Microphone] = None

        self.running = False
        self._lock = threading.RLock()

        self.logger = logging.getLogger("NEO.VoiceListener")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Voice] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._init_microphone()

        # Subscribe control events
        self.event_bus.subscribe("voice.start", self._start_listener, priority=9)
        self.event_bus.subscribe("voice.stop", self._stop_listener, priority=9)

    # =========================
    # Initialization
    # =========================

    def _init_microphone(self):
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.logger.info("Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            self.logger.error(f"Microphone init failed: {e}")
            self.logger.debug(traceback.format_exc())

    # =========================
    # Start/Stop
    # =========================

    def _start_listener(self, event: Event):
        with self._lock:
            if self.running:
                self.logger.warning("Listener already running")
                return

            self.running = True
            threading.Thread(target=self._listen_loop, daemon=True).start()
            self.logger.info("Voice listener started")

    def _stop_listener(self, event: Event):
        with self._lock:
            self.running = False
            self.logger.info("Voice listener stopped")

    # =========================
    # Listening Loop
    # =========================

    def _listen_loop(self):
        while self.running:
            try:
                with self.microphone as source:
                    self.logger.debug("Listening...")
                    audio = self.recognizer.listen(
                        source,
                        timeout=5,
                        phrase_time_limit=8
                    )

                text = self._recognize(audio)

                if text:
                    self.logger.info(f"Heard: {text}")

                    self.event_bus.publish(
                        "voice.command",
                        {"text": text},
                        priority=9,
                    )

            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Listening error: {e}")
                self.logger.debug(traceback.format_exc())

            time.sleep(0.1)

    # =========================
    # Recognition
    # =========================

    def _recognize(self, audio) -> Optional[str]:
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            self.logger.debug("Could not understand audio")
        except sr.RequestError as e:
            self.logger.error(f"API error: {e}")
        except Exception as e:
            self.logger.error(f"Recognition failed: {e}")
            self.logger.debug(traceback.format_exc())

        return None


# =========================
# GLOBAL INSTANCE
# =========================

GlobalVoiceListener = VoiceListener()