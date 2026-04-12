"""
vision/__init__.py

NEO AI OS - Vision Module Manager

Responsibilities:
- Initialize and manage all vision subsystems
- Integrate Object Detection, Face Recognition, OCR
- Handle lifecycle (start/stop)
- Track vision metrics (detections, recognitions, errors)
- EventBus integration

"""

from __future__ import annotations

import threading
import logging
import traceback
import time
from typing import Dict, Any

from core.event_bus import GlobalEventBus, Event
from vision.object_detection import GlobalObjectDetector
from vision.face_recognition import GlobalFaceRecognition
from vision.ocr_reader import GlobalOCRReader


class VisionError(Exception):
    pass


class VisionManager:
    def __init__(self):
        self.event_bus = GlobalEventBus

        self.object_detector = GlobalObjectDetector
        self.face_recognition = GlobalFaceRecognition
        self.ocr = GlobalOCRReader

        self._lock = threading.RLock()
        self._running = False

        # Metrics
        self.start_time: float = 0.0
        self.objects_detected: int = 0
        self.faces_detected: int = 0
        self.text_extracted: int = 0
        self.errors: int = 0

        # Logger
        self.logger = logging.getLogger("NEO.Vision.Manager")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Vision.Manager] %(message)s"
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

                self.logger.info("Vision Manager started")
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
                self.logger.info("Vision Manager stopped")
                return True

            except Exception as e:
                self._error("stop", e)
                return False

    def is_running(self) -> bool:
        return self._running

    # =========================
    # Metrics
    # =========================

    def _inc_object(self):
        with self._lock:
            self.objects_detected += 1

    def _inc_face(self):
        with self._lock:
            self.faces_detected += 1

    def _inc_text(self):
        with self._lock:
            self.text_extracted += 1

    def _inc_error(self):
        with self._lock:
            self.errors += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time if self._running else 0

            return {
                "status": "running" if self._running else "stopped",
                "uptime": round(uptime, 2),
                "objects_detected": self.objects_detected,
                "faces_detected": self.faces_detected,
                "text_extracted": self.text_extracted,
                "errors": self.errors,
            }

    # =========================
    # Event Handling
    # =========================

    def _subscribe_events(self):
        try:
            self.event_bus.subscribe("vision.object.detected", self._on_object, priority=8)
            self.event_bus.subscribe("vision.face.detected", self._on_face, priority=8)
            self.event_bus.subscribe("vision.text.extracted", self._on_text, priority=8)
            self.event_bus.subscribe("system.shutdown", self._on_shutdown, priority=10)
        except Exception as e:
            self._error("subscribe", e)

    def _on_object(self, event: Event):
        try:
            self._inc_object()
        except Exception as e:
            self._error("object_event", e)

    def _on_face(self, event: Event):
        try:
            self._inc_face()
        except Exception as e:
            self._error("face_event", e)

    def _on_text(self, event: Event):
        try:
            self._inc_text()
        except Exception as e:
            self._error("text_event", e)

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
                "system.error.vision_manager",
                {"source": source, "error": str(error)},
                priority=10,
            )
        except Exception:
            pass


# =========================
# GLOBAL INSTANCE
# =========================

GlobalVisionManager = VisionManager()