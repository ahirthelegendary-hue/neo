"""
vision/face_recognition.py

NEO AI OS - Face Recognition Module
"""

from __future__ import annotations

import os
import cv2
import pickle
import threading
import logging
import traceback
import time
import asyncio
from typing import Dict, Any, List, Tuple

import face_recognition
import numpy as np

from core.event_bus import GlobalEventBus, Event


class FaceRecognitionError(Exception):
    """Face recognition exception"""


class FaceRecognitionSystem:
    """
    Face recognition engine.
    """

    def __init__(self, db_path: str = "data/faces.pkl"):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.db_path = db_path
        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []

        self.running = False

        self.logger = logging.getLogger("NEO.FaceRecognition")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Face] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # FIX: _load_db call aur subscriptions ko __init__ ke andar rakha hai
        self._load_db()

        # Event subscriptions
        self.event_bus.subscribe("vision.face.start", self._start, priority=9)
        self.event_bus.subscribe("vision.face.stop", self._stop, priority=9)
        self.event_bus.subscribe("vision.face.add", self._on_add_face, priority=9)

    # =========================
    # Database Handling
    # =========================

    def _load_db(self):
        self.logger.info("Face database loading initialized...")
        pass

    def _load_model(self):
        try:
            base_path = os.path.dirname(os.path.dirname(__file__))

            proto = os.path.join(base_path, "models", "MobileNetSSD_deploy.prototxt")
            model = os.path.join(base_path, "models", "MobileNetSSD_deploy.caffemodel")

            if not os.path.exists(proto) or not os.path.exists(model):
                self.logger.error("Model files not found")
                return None

            net = cv2.dnn.readNetFromCaffe(proto, model)
            self.logger.info("Vision model loaded successfully")
            return net

        except Exception as e:
            self._error("load_model", e)
            return None

    def _save_db(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, "wb") as f:
                pickle.dump({
                    "encodings": self.known_encodings,
                    "names": self.known_names
                }, f)
        except Exception as e:
            self._error("save_db", e)

    # =========================
    # Detection Loop
    # =========================

    def _loop(self):
        cap = cv2.VideoCapture(0)

        while self.running:
            try:
                ret, frame = cap.read()
                if not ret:
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(rgb)
                face_encodings = face_recognition.face_encodings(rgb, face_locations)

                detected_faces = []

                for encoding, loc in zip(face_encodings, face_locations):
                    matches = face_recognition.compare_faces(self.known_encodings, encoding)
                    name = "Unknown"

                    if True in matches:
                        idx = matches.index(True)
                        name = self.known_names[idx]

                    detected_faces.append({
                        "name": name,
                        "location": loc
                    })

                    # Draw box
                    top, right, bottom, left = loc
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, name, (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                if detected_faces:
                    self.event_bus.publish(
                        "vision.face.detected",
                        {"faces": detected_faces},
                        priority=8,
                    )

                cv2.imshow("NEO Face Recognition", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            except Exception as e:
                self._error("loop", e)

            time.sleep(0.05)

        cap.release()
        cv2.destroyAllWindows()

    # =========================
    # Add Face
    # =========================

    def add_face(self, name: str, image_path: str) -> bool:
        try:
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)

            if not encodings:
                raise FaceRecognitionError("No face found in image")

            self.known_encodings.append(encodings[0])
            self.known_names.append(name)

            self._save_db()

            self._emit("vision.face.added", {"name": name})
            return True

        except Exception as e:
            self._error("add_face", e)
            return False

    # =========================
    # Event Handlers
    # =========================

    def _start(self, event: Event):
        if not self.running:
            self.running = True
            threading.Thread(target=self._loop, daemon=True).start()
            self.logger.info("Face recognition started")

    def _stop(self, event: Event):
        self.running = False
        self.logger.info("Face recognition stopped")

    def _on_add_face(self, event: Event):
        try:
            name = event.data.get("name")
            path = event.data.get("path")

            if name and path:
                self.add_face(name, path)
        except Exception as e:
            self._error("event_add_face", e)

    # =========================
    # Helpers
    # =========================

    def _emit(self, name: str, data: Dict[str, Any]):
        try:
            self.event_bus.publish(name, data, priority=7)
        except Exception:
            pass

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.face",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def add_face_async(self, name: str, image_path: str):
        return await asyncio.to_thread(self.add_face, name, image_path)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalFaceRecognition = FaceRecognitionSystem()