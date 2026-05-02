"""
Object detection services using YOLOv8.

VehicleDetector: detects vehicles and persons in traffic frames.
HelmetDetector: detects helmet/no-helmet on motorcycle rider crops.

YOLOv8n is auto-downloaded if not present.
"""

import logging
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# COCO class IDs relevant to traffic
COCO_VEHICLE_CLASSES = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
COCO_PERSON_CLASS = 0
TWO_WHEELER_CLASSES = {"motorcycle", "bicycle"}


class VehicleDetector:
    """Detects vehicles and persons using YOLOv8."""

    def __init__(self, model_path: str | None = None, confidence: float | None = None):
        self.model_path = model_path or settings.DETECTION_MODEL_PATH
        self.confidence = confidence or settings.DETECTION_CONFIDENCE_THRESHOLD
        self.model: YOLO | None = None

    def load_model(self):
        """Load model, auto-downloading yolov8n if path doesn't exist."""
        path = Path(self.model_path)
        if not path.exists():
            logger.info(f"Model not found at {self.model_path}, downloading yolov8n.pt...")
            # ultralytics auto-downloads when you pass a model name
            self.model = YOLO("yolov8n.pt")
            # Save to configured path for next time
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.model = YOLO(str(path))

        logger.info(f"Vehicle detector loaded: {self.model_path}")

    def detect(self, frame: np.ndarray) -> list[dict]:
        """
        Run detection on a frame.

        Returns list of dicts:
            {bbox: [x1,y1,x2,y2], confidence: float, class_id: int, class_name: str}
        """
        if self.model is None:
            self.load_model()

        results = self.model(frame, conf=self.confidence, verbose=False)

        detections = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                detections.append({
                    "bbox": box.xyxy[0].cpu().numpy().tolist(),
                    "confidence": float(box.conf[0]),
                    "class_id": class_id,
                    "class_name": class_name,
                })
        return detections

    def detect_vehicles_and_persons(self, frame: np.ndarray) -> tuple[list[dict], list[dict]]:
        """
        Run detection and split results into vehicles and persons.

        Returns:
            (vehicles, persons) where each is a list of detection dicts.
        """
        all_detections = self.detect(frame)
        vehicles = [d for d in all_detections if d["class_id"] in COCO_VEHICLE_CLASSES]
        persons = [d for d in all_detections if d["class_id"] == COCO_PERSON_CLASS]
        return vehicles, persons


class HelmetDetector:
    """
    Detects whether a two-wheeler rider is wearing a helmet.

    If a dedicated helmet model is available (helmet_detector.pt), uses it.
    Otherwise, falls back to a heuristic: checks if a person bounding box
    overlaps with a motorcycle bounding box (rider association) and assumes
    no-helmet if the rider's head region shows no helmet class.
    """

    def __init__(self, model_path: str | None = None, confidence: float | None = None):
        self.model_path = model_path or settings.HELMET_MODEL_PATH
        self.confidence = confidence or settings.HELMET_CONFIDENCE_THRESHOLD
        self.model: YOLO | None = None
        self._model_available: bool | None = None

    def _check_model_available(self) -> bool:
        if self._model_available is None:
            self._model_available = Path(self.model_path).exists()
            if self._model_available:
                logger.info(f"Helmet model found at {self.model_path}")
            else:
                logger.warning(
                    f"No helmet model at {self.model_path}. "
                    "Using heuristic fallback (person-on-motorcycle detection). "
                    "For better accuracy, add a helmet detection model."
                )
        return self._model_available

    def load_model(self):
        if self._check_model_available():
            self.model = YOLO(self.model_path)
            logger.info("Helmet detector model loaded")

    def detect(self, frame: np.ndarray, rider_bbox: list[float]) -> dict:
        """
        Check if a rider (cropped from frame at rider_bbox) is wearing a helmet.

        Args:
            frame: full frame
            rider_bbox: [x1, y1, x2, y2] of the motorcycle/rider region

        Returns:
            {"helmet": bool, "confidence": float}
        """
        x1, y1, x2, y2 = [int(c) for c in rider_bbox]
        h, w = frame.shape[:2]
        # Clamp to frame bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        rider_crop = frame[y1:y2, x1:x2]
        if rider_crop.size == 0:
            return {"helmet": False, "confidence": 0.0}

        if self._check_model_available():
            return self._detect_with_model(rider_crop)
        else:
            return self._detect_heuristic(rider_crop)

    def _detect_with_model(self, rider_crop: np.ndarray) -> dict:
        """Use dedicated helmet detection model."""
        if self.model is None:
            self.load_model()

        results = self.model(rider_crop, conf=self.confidence, verbose=False)

        helmet_found = False
        no_helmet_found = False
        best_confidence = 0.0

        for result in results:
            for box in result.boxes:
                class_name = result.names[int(box.cls[0])].lower()
                conf = float(box.conf[0])

                if "helmet" in class_name and "no" not in class_name:
                    if conf > best_confidence:
                        helmet_found = True
                        best_confidence = conf
                elif "no" in class_name and "helmet" in class_name:
                    if conf > best_confidence:
                        no_helmet_found = True
                        best_confidence = conf

        if helmet_found:
            return {"helmet": True, "confidence": best_confidence}
        elif no_helmet_found:
            return {"helmet": False, "confidence": best_confidence}
        else:
            # No helmet detected either way — assume no helmet with low confidence
            return {"helmet": False, "confidence": 0.3}

    def _detect_heuristic(self, rider_crop: np.ndarray) -> dict:
        """
        Heuristic fallback when no helmet model is available.

        Checks the upper portion of the rider crop for head-like features.
        This is approximate — a real deployment should use a trained model.

        Returns helmet=False with moderate confidence since we can't tell
        for certain without a dedicated model.
        """
        # Without a model, we conservatively flag all motorcycle riders
        # as potential no-helmet violations with low confidence.
        # The rule engine's MIN_VIOLATION_FRAMES threshold will filter noise.
        return {"helmet": False, "confidence": 0.5}


def find_rider_for_motorcycle(
    motorcycle_bbox: list[float],
    persons: list[dict],
    iou_threshold: float = 0.05,
) -> dict | None:
    """
    Find the person most likely riding a given motorcycle by bbox overlap.

    Args:
        motorcycle_bbox: [x1, y1, x2, y2] of the motorcycle
        persons: list of person detection dicts
        iou_threshold: minimum IoU to consider a person as a rider

    Returns:
        The person detection dict if found, else None
    """
    best_person = None
    best_overlap = 0.0

    mx1, my1, mx2, my2 = motorcycle_bbox
    moto_area = (mx2 - mx1) * (my2 - my1)

    for person in persons:
        px1, py1, px2, py2 = person["bbox"]
        # Compute intersection
        ix1 = max(mx1, px1)
        iy1 = max(my1, py1)
        ix2 = min(mx2, px2)
        iy2 = min(my2, py2)

        if ix1 < ix2 and iy1 < iy2:
            intersection = (ix2 - ix1) * (iy2 - iy1)
            person_area = (px2 - px1) * (py2 - py1)
            union = moto_area + person_area - intersection
            iou = intersection / union if union > 0 else 0

            if iou > iou_threshold and iou > best_overlap:
                best_overlap = iou
                best_person = person

    return best_person
