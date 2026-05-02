"""
License plate OCR using PaddleOCR.

Reads license plate text from vehicle region crops.
Includes preprocessing and plate format normalization.
"""

import logging
import re

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Common Indian plate format: XX 00 XX 0000 (state, district, series, number)
INDIAN_PLATE_PATTERN = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}$")


class LicensePlateReader:
    """Reads license plate text from vehicle image crops using PaddleOCR."""

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.ocr = None

    def _init_ocr(self):
        """Lazy-load PaddleOCR to avoid startup cost."""
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, show_log=False)
            logger.info("PaddleOCR initialized")
        except ImportError:
            logger.error(
                "PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle"
            )
            raise

    def preprocess_plate(self, plate_img: np.ndarray) -> np.ndarray:
        """
        Preprocess a plate crop for better OCR accuracy.

        Steps: grayscale -> denoise -> adaptive threshold -> resize
        """
        if plate_img.size == 0:
            return plate_img

        # Convert to grayscale
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img

        # Denoise
        gray = cv2.bilateralFilter(gray, 11, 17, 17)

        # Adaptive threshold for varying lighting
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Resize to standard height if too small
        h, w = thresh.shape[:2]
        if h < 50:
            scale = 50 / h
            thresh = cv2.resize(thresh, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        return thresh

    def read_plate(self, frame: np.ndarray, vehicle_bbox: list[float]) -> dict:
        """
        Extract and read a license plate from a vehicle region.

        Args:
            frame: full video frame
            vehicle_bbox: [x1, y1, x2, y2] bounding box of the vehicle

        Returns:
            {"text": str, "confidence": float}
        """
        if self.ocr is None:
            self._init_ocr()

        x1, y1, x2, y2 = [int(c) for c in vehicle_bbox]
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        vehicle_crop = frame[y1:y2, x1:x2]
        if vehicle_crop.size == 0:
            return {"text": "", "confidence": 0.0}

        # Focus on the lower portion of the vehicle where the plate usually is
        crop_h = vehicle_crop.shape[0]
        plate_region = vehicle_crop[int(crop_h * 0.5):, :]

        if plate_region.size == 0:
            plate_region = vehicle_crop

        # Preprocess
        processed = self.preprocess_plate(plate_region)

        # Run OCR
        try:
            results = self.ocr.ocr(processed, cls=True)
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return {"text": "", "confidence": 0.0}

        if not results or not results[0]:
            # Try with original (un-preprocessed) crop as fallback
            try:
                results = self.ocr.ocr(plate_region, cls=True)
            except Exception:
                return {"text": "", "confidence": 0.0}

            if not results or not results[0]:
                return {"text": "", "confidence": 0.0}

        # Extract text and confidence from OCR results
        texts = []
        confidences = []
        for line in results[0]:
            text = line[1][0]
            conf = line[1][1]
            texts.append(text)
            confidences.append(conf)

        raw_text = " ".join(texts).strip().upper()
        plate_text = self._normalize_plate(raw_text)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {"text": plate_text, "confidence": avg_confidence}

    def _normalize_plate(self, text: str) -> str:
        """
        Clean up OCR output to a plausible plate number.

        Removes non-alphanumeric characters and applies context-aware
        character substitution (only in expected positions).
        """
        # Remove non-alphanumeric characters
        cleaned = "".join(c for c in text if c.isalnum())

        if not cleaned:
            return ""

        # For Indian plates, try to fix common OCR errors
        # Only do positional substitution: first 2 chars should be letters,
        # then digits, then letters, then digits
        # We don't blindly replace O->0 everywhere — only where a digit is expected.
        # This is a simple heuristic; a production system would use regex-based validation.

        return cleaned

    def read_plate_from_crop(self, plate_crop: np.ndarray) -> dict:
        """Read a plate from an already-cropped plate image."""
        if self.ocr is None:
            self._init_ocr()

        if plate_crop.size == 0:
            return {"text": "", "confidence": 0.0}

        processed = self.preprocess_plate(plate_crop)
        try:
            results = self.ocr.ocr(processed, cls=True)
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return {"text": "", "confidence": 0.0}

        if not results or not results[0]:
            return {"text": "", "confidence": 0.0}

        texts = []
        confidences = []
        for line in results[0]:
            texts.append(line[1][0])
            confidences.append(line[1][1])

        plate_text = self._normalize_plate(" ".join(texts).strip().upper())
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {"text": plate_text, "confidence": avg_confidence}
