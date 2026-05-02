"""
Traffic violation rule engine.

Applies rules to tracked vehicles to detect violations.
Uses frame-count-based confirmation to reduce false positives.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.app.core.config import settings
from backend.app.models.violation import ViolationType

logger = logging.getLogger(__name__)


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class TrafficRule:
    camera_id: str
    allowed_direction: Direction | None = None
    signal_zone: tuple[int, int, int, int] | None = None
    speed_limit_kmh: float | None = None


@dataclass
class ViolationCandidate:
    """Tracks a potential violation across frames before confirming."""
    tracker_id: int
    violation_type: ViolationType
    first_frame: int
    frame_count: int = 1
    total_confidence: float = 0.0
    best_frame_id: int = 0
    best_confidence: float = 0.0
    best_bbox: list[float] = field(default_factory=list)
    details: str = ""
    confirmed: bool = False

    @property
    def avg_confidence(self) -> float:
        return self.total_confidence / self.frame_count if self.frame_count > 0 else 0.0


class ViolationRuleEngine:
    """
    Evaluates traffic rules and confirms violations.

    A violation is only confirmed after being detected in MIN_VIOLATION_FRAMES
    consecutive frames for the same tracked object. This dramatically reduces
    false positives from single-frame detection noise.
    """

    def __init__(self, min_frames: int | None = None):
        self.rules: dict[str, TrafficRule] = {}
        self.min_frames = min_frames or settings.MIN_VIOLATION_FRAMES
        # tracker_id -> {violation_type -> ViolationCandidate}
        self._candidates: dict[int, dict[ViolationType, ViolationCandidate]] = defaultdict(dict)
        # Set of confirmed (tracker_id, violation_type) to avoid duplicates
        self._confirmed: set[tuple[int, str]] = set()

    def register_rule(self, rule: TrafficRule):
        self.rules[rule.camera_id] = rule

    def check_helmet_violation(
        self,
        tracker_id: int,
        has_helmet: bool,
        vehicle_class: str,
        confidence: float,
        frame_id: int,
        bbox: list[float],
    ) -> dict | None:
        """
        Check if a tracked motorcycle rider is missing a helmet.

        Returns a violation dict only when confirmed across enough frames.
        Returns None if not yet confirmed or already reported.
        """
        two_wheelers = {"motorcycle", "bicycle", "motorbike"}
        if vehicle_class.lower() not in two_wheelers:
            return None

        key = (tracker_id, ViolationType.HELMET_VIOLATION.value)

        # Already confirmed this violation for this track — skip
        if key in self._confirmed:
            return None

        if not has_helmet and confidence > 0.3:
            # Update or create candidate
            candidates = self._candidates[tracker_id]
            if ViolationType.HELMET_VIOLATION not in candidates:
                candidates[ViolationType.HELMET_VIOLATION] = ViolationCandidate(
                    tracker_id=tracker_id,
                    violation_type=ViolationType.HELMET_VIOLATION,
                    first_frame=frame_id,
                    best_bbox=bbox,
                    details="Rider without helmet detected",
                )

            candidate = candidates[ViolationType.HELMET_VIOLATION]
            candidate.frame_count += 1
            candidate.total_confidence += confidence
            if confidence > candidate.best_confidence:
                candidate.best_confidence = confidence
                candidate.best_frame_id = frame_id
                candidate.best_bbox = bbox

            # Check if we have enough frames to confirm
            if candidate.frame_count >= self.min_frames and not candidate.confirmed:
                candidate.confirmed = True
                self._confirmed.add(key)
                logger.info(
                    f"Helmet violation CONFIRMED for track {tracker_id} "
                    f"({candidate.frame_count} frames, avg conf {candidate.avg_confidence:.2f})"
                )
                return {
                    "violation_type": ViolationType.HELMET_VIOLATION,
                    "details": candidate.details,
                    "frame_count": candidate.frame_count,
                    "avg_confidence": candidate.avg_confidence,
                }
        else:
            # Helmet detected or low confidence — reset candidate
            self._candidates[tracker_id].pop(ViolationType.HELMET_VIOLATION, None)

        return None

    def check_wrong_way(
        self, camera_id: str, tracker_id: int, direction: str | None, frame_id: int
    ) -> dict | None:
        """Check if a vehicle is traveling in the wrong direction."""
        rule = self.rules.get(camera_id)
        if not rule or not rule.allowed_direction or direction is None:
            return None

        key = (tracker_id, ViolationType.WRONG_WAY.value)
        if key in self._confirmed:
            return None

        if direction != rule.allowed_direction.value:
            self._confirmed.add(key)
            return {
                "violation_type": ViolationType.WRONG_WAY,
                "details": f"Vehicle traveling {direction}, expected {rule.allowed_direction.value}",
            }
        return None

    def check_signal_jump(
        self,
        camera_id: str,
        tracker_id: int,
        bbox: list[float],
        signal_state: str,
    ) -> dict | None:
        """Check if a vehicle entered the signal zone during red light."""
        rule = self.rules.get(camera_id)
        if not rule or not rule.signal_zone:
            return None

        if signal_state != "red":
            return None

        key = (tracker_id, ViolationType.SIGNAL_JUMP.value)
        if key in self._confirmed:
            return None

        zx1, zy1, zx2, zy2 = rule.signal_zone
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2

        if zx1 <= cx <= zx2 and zy1 <= cy <= zy2:
            self._confirmed.add(key)
            return {
                "violation_type": ViolationType.SIGNAL_JUMP,
                "details": "Vehicle crossed stop line during red signal",
            }
        return None

    def reset_track(self, tracker_id: int):
        """Clear candidates for a track that has left the scene."""
        self._candidates.pop(tracker_id, None)

    def reset(self):
        """Full reset of all state."""
        self._candidates.clear()
        self._confirmed.clear()
