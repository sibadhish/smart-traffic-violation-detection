"""
End-to-end traffic violation detection pipeline.

Flow: detect vehicles → track → check violations → read plates → generate evidence
"""

import logging
from datetime import datetime

import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.services.detection.detector import (
    HelmetDetector,
    VehicleDetector,
    TWO_WHEELER_CLASSES,
    find_rider_for_motorcycle,
)
from backend.app.services.ocr.plate_reader import LicensePlateReader
from backend.app.services.tracking.tracker import VehicleTracker
from backend.app.services.violations.rule_engine import ViolationRuleEngine

logger = logging.getLogger(__name__)


class TrafficPipeline:
    """
    End-to-end pipeline: detect -> track -> check violations -> read plates.

    Maintains a frame buffer for clip extraction around violation events.
    """

    def __init__(self, camera_id: str, rule_engine: ViolationRuleEngine | None = None):
        self.camera_id = camera_id
        self.detector = VehicleDetector()
        self.helmet_detector = HelmetDetector()
        self.plate_reader = LicensePlateReader()
        self.tracker = VehicleTracker()
        self.rule_engine = rule_engine or ViolationRuleEngine()

        self.frame_buffer: list[np.ndarray] = []
        self.frame_id = 0
        self.max_buffer_frames = int(
            settings.VIDEO_FPS * (settings.CLIP_SECONDS_BEFORE + settings.CLIP_SECONDS_AFTER + 5)
        )

    def process_frame(self, frame: np.ndarray) -> list[dict]:
        """
        Process a single frame through the full pipeline.

        Returns a list of confirmed violation dicts (may be empty).
        """
        self.frame_id += 1
        self._buffer_frame(frame)

        # Step 1: Detect vehicles and persons
        vehicles, persons = self.detector.detect_vehicles_and_persons(frame)

        # Step 2: Track detected vehicles
        tracked = self.tracker.update(vehicles, self.frame_id)

        # Step 3: Check each tracked object for violations
        violations = []
        for track in tracked:
            violation = self._check_violations(frame, track, persons)
            if violation:
                violations.append(violation)

        return violations

    def _check_violations(
        self, frame: np.ndarray, track: dict, persons: list[dict]
    ) -> dict | None:
        """Run all violation checks for a single tracked object."""
        tracker_id = track["tracker_id"]
        class_name = track.get("class_name", self._get_class_name(track["class_id"]))
        bbox = track["bbox"]

        # Check wrong-way driving
        direction = self.tracker.get_track_direction(tracker_id)
        wrong_way = self.rule_engine.check_wrong_way(
            self.camera_id, tracker_id, direction, self.frame_id
        )
        if wrong_way:
            plate = self._read_plate_safe(frame, bbox)
            return self._build_violation_result(wrong_way, track, plate)

        # Check helmet violations for two-wheelers
        if class_name in TWO_WHEELER_CLASSES:
            # Try to find the rider (person) on the motorcycle
            rider = find_rider_for_motorcycle(bbox, persons)
            check_bbox = rider["bbox"] if rider else bbox

            helmet_result = self.helmet_detector.detect(frame, check_bbox)
            helmet_violation = self.rule_engine.check_helmet_violation(
                tracker_id=tracker_id,
                has_helmet=helmet_result["helmet"],
                vehicle_class=class_name,
                confidence=helmet_result["confidence"],
                frame_id=self.frame_id,
                bbox=bbox,
            )
            if helmet_violation:
                plate = self._read_plate_safe(frame, bbox)
                return self._build_violation_result(helmet_violation, track, plate)

        return None

    def _build_violation_result(
        self, violation: dict, track: dict, plate: dict
    ) -> dict:
        """Combine violation + track + plate info into a result dict."""
        return {
            **violation,
            "tracker_id": track["tracker_id"],
            "bbox": track["bbox"],
            "confidence": violation.get("avg_confidence", track["confidence"]),
            "license_plate": plate["text"] if plate["confidence"] > 0.4 else None,
            "plate_confidence": plate["confidence"],
            "frame_id": self.frame_id,
            "camera_id": self.camera_id,
            "detected_at": datetime.utcnow().isoformat(),
        }

    def _read_plate_safe(self, frame: np.ndarray, bbox: list[float]) -> dict:
        """Read plate with error handling."""
        try:
            return self.plate_reader.read_plate(frame, bbox)
        except Exception as e:
            logger.warning(f"Plate reading failed: {e}")
            return {"text": "", "confidence": 0.0}

    def _get_class_name(self, class_id: int) -> str:
        """Map COCO class IDs to names."""
        coco_vehicles = {
            1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck",
        }
        return coco_vehicles.get(class_id, "unknown")

    def _buffer_frame(self, frame: np.ndarray):
        """Maintain a rolling buffer of recent frames for clip extraction."""
        self.frame_buffer.append(frame.copy())
        if len(self.frame_buffer) > self.max_buffer_frames:
            self.frame_buffer.pop(0)

    def get_clip_frames(
        self, frame_id: int, before: int | None = None, after: int | None = None
    ) -> list[np.ndarray]:
        """
        Get frames around a given frame_id for clip extraction.

        Args:
            frame_id: the frame number to center the clip on
            before: number of frames before (default from settings)
            after: number of frames after (default from settings)
        """
        before = before or int(settings.CLIP_SECONDS_BEFORE * settings.VIDEO_FPS)
        after = after or int(settings.CLIP_SECONDS_AFTER * settings.VIDEO_FPS)

        # Convert frame_id to buffer index
        buffer_start_frame = self.frame_id - len(self.frame_buffer) + 1
        idx = frame_id - buffer_start_frame

        start = max(0, idx - before)
        end = min(len(self.frame_buffer), idx + after)
        return self.frame_buffer[start:end]

    def get_frame_at(self, frame_id: int) -> np.ndarray | None:
        """Get a specific frame from the buffer."""
        buffer_start_frame = self.frame_id - len(self.frame_buffer) + 1
        idx = frame_id - buffer_start_frame
        if 0 <= idx < len(self.frame_buffer):
            return self.frame_buffer[idx]
        return None

    def reset(self):
        """Reset the pipeline state."""
        self.tracker.reset()
        self.rule_engine.reset()
        self.frame_buffer.clear()
        self.frame_id = 0
