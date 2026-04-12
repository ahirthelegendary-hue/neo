"""
vision/ocr_reader.py

NEO AI OS - OCR (Optical Character Recognition) Module

Responsibilities:
- Extract text from images (screenshots, camera, files)
- Preprocess images for better OCR accuracy
- Support real-time OCR via webcam
- Emit extracted text via EventBus
- Provide utility functions for screen OCR

Features:
- Uses Tesseract OCR
- Image preprocessing (grayscale, thresholding)
- Real-time OCR loop
- Thread-safe
- Async + Sync support
- Event-driven output

Dependencies:
pip install pytesseract opencv-python numpy
Install Tesseract:
- Windows: install from official site and set PATH
- Linux: sudo apt install tesseract-ocr
"""

from __future__ import annotations

import cv2
import numpy as np
import pytesseract
import threading
import logging
import traceback
import time
import asyncio
from typing import Dict, Any, Optional

import os

# --- TESSERACT ENGINE PATH ---
tesseract_exe_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

if os.path.exists(tesseract_exe_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
else:
    print("❌ ALERT: Tesseract Engine nahi mila!")

from core.event_bus import GlobalEventBus, Event


class OCRError(Exception):
    """OCR exception"""


class OCRReader:
    """
    Extract text from images or video stream.
    """

    def __init__(self):
        self.event_bus = GlobalEventBus
        self._lock = threading.RLock()

        self.running = False

        self.logger = logging.getLogger("NEO.OCR")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [OCR] %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Event subscriptions
        self.event_bus.subscribe("vision.ocr.start", self._start, priority=9)
        self.event_bus.subscribe("vision.ocr.stop", self._stop, priority=9)
        self.event_bus.subscribe("vision.ocr.image", self._on_image, priority=9)

    # =========================
    # Core OCR
    # =========================

    def extract_text(self, image) -> str:
        try:
            processed = self._preprocess(image)
            text = pytesseract.image_to_string(processed)
            return text.strip()
        except Exception as e:
            self._error("extract_text", e)
            return ""

    def _preprocess(self, image):
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        except Exception as e:
            self._error("preprocess", e)
            return image

    # =========================
    # Real-Time OCR Loop
    # =========================

    def _loop(self):
        cap = cv2.VideoCapture(0)

        while self.running:
            try:
                ret, frame = cap.read()
                if not ret:
                    continue

                text = self.extract_text(frame)

                if text:
                    self.logger.info(f"OCR Text: {text}")

                    self.event_bus.publish(
                        "vision.ocr.result",
                        {"text": text},
                        priority=8,
                    )

                cv2.imshow("NEO OCR", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            except Exception as e:
                self._error("loop", e)

            time.sleep(0.1)

        cap.release()
        cv2.destroyAllWindows()

    # =========================
    # Event Handlers
    # =========================

    def _start(self, event: Event):
        if not self.running:
            self.running = True
            threading.Thread(target=self._loop, daemon=True).start()
            self.logger.info("OCR started")

    def _stop(self, event: Event):
        self.running = False
        self.logger.info("OCR stopped")

    def _on_image(self, event: Event):
        try:
            image = event.data.get("image")
            if image is not None:
                text = self.extract_text(image)

                self.event_bus.publish(
                    "vision.ocr.result",
                    {"text": text},
                    priority=8,
                )
        except Exception as e:
            self._error("event_image", e)

    # =========================
    # Helpers
    # =========================

    def _error(self, source: str, error: Exception):
        self.logger.error(f"{source} error: {error}")
        self.logger.debug(traceback.format_exc())

        try:
            self.event_bus.publish(
                "system.error.ocr",
                {"source": source, "error": str(error)},
                priority=9,
            )
        except Exception:
            pass

    # =========================
    # Async API
    # =========================

    async def extract_text_async(self, image):
        return await asyncio.to_thread(self.extract_text, image)


# =========================
# GLOBAL INSTANCE
# =========================

GlobalOCRReader = OCRReader()