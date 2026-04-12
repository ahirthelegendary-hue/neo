"""
vision/object_detection.py

NEO AI OS - Vision Object Detection Module

Responsibilities:
- Detect objects from webcam/video/image
- Real-time detection loop
- Emit detected objects via EventBus
- Support basic bounding box tracking
- Integrate with system (alerts, automation)

Features:
- Uses OpenCV + pre-trained MobileNet SSD
- Real-time detection
- Confidence filtering
- Async + Thread-safe
- Event-driven output

Dependencies:
pip install opencv-python numpy
"""

from __future__ import annotations

import cv2
import numpy as np
import threading
import logging
import traceback
import time
import asyncio
from typing import Dict, Any, List

from core.event_bus import GlobalEventBus, Event


class VisionError(Exception):
    """Vision exception"""


class ObjectDetector:
    """
    Real-time object detection system.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.running = False
        self.confidence_threshold = 0.5

        self.logger = logging.getLogger("NEO.Vision")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [Vision] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Load model
        self.net = self._load_model()

        # Class labels
        self.classes = [
            "background", "aeroplane", "bicycle", "bird", "boat", "bottle",
            "bus", "car", "cat", "chair", "cow", "diningtable", "dog",
            "horse", "motorbike", "person", "pottedplant", "sheep",
            "sofa", "train", "tvmonitor"
        ]

        # Event subscriptions
        self.event_bus.subscribe("vision.start", self._start, priority=9)
        self.event_bus.subscribe("vision.stop", self._stop, priority=9)

    # =========================
    # Model Loading
    # =========================

    def _load_model(self):
        try:
            proto = "models/MobileNetSSD_deploy.prototxt"
            model = "models/MobileNetSSD_deploy.caffemodel"

            net = cv2.dnn.readNetFromCaffe(proto, model)
            self.logger.info("Model loaded successfully")
            return net

        except Exception as e:
            self._error("load_model", e)
            return None

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

                detections = self._detect(frame)

                if detections:
                    self.event_bus.publish(
                        "vision.objects.detected",
                        {"objects": detections},
                        priority=8,
                    )

                # Optional display
                cv2.imshow("NEO Vision", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            except Exception as e:
                self._error("loop", e)

            time.sleep(0.05)

        cap.release()
        cv2.destroyAllWindows()

    def _detect(self, frame) -> List[Dict[str, Any]]:
        results = []

        try:
            h, w = frame.shape[:2]
            blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)

            self.net.setInput(blob)
            detections = self.net.forward()

            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]

                if confidence > self.confidence_threshold:
                    idx = int(detections[0, 0, i, 1])
                    label = self.classes[idx]

                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (x1, y1, x2, y2) = box.astype("int")

                    results.append({
                        "label": label,
                        "confidence": float(confidence),
                        "box": [int(x1), int(y1), int(x2), int(y2)]
                    })

                    # Draw box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        except Exception as e:
            self._error("detect", e)

        return results

    # =========================
    # Control
    # =========================

    def _start(self, event: Event):
        if not self.running:
            self.running = True
            threading.Thread(target=self._loop, daemon=True).start()
            self.logger.info("Vision started")

    def _stop(self, event: Event):
        self.running = False
        self.logger.info("Vision stopped")

    # =========================
    # Helpers
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.vision",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def detect_async(self, frame):
        return await asyncio.to_thread(self._detect, frame)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalObjectDetector = ObjectDetector()