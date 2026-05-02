"""Tests for the traffic violation rule engine."""

import pytest

from backend.app.models.violation import ViolationType
from backend.app.services.violations.rule_engine import (
    Direction,
    TrafficRule,
    ViolationRuleEngine,
)


@pytest.fixture
def engine():
    return ViolationRuleEngine(min_frames=3)


@pytest.fixture
def engine_with_rule(engine):
    rule = TrafficRule(
        camera_id="cam-01",
        allowed_direction=Direction.DOWN,
        signal_zone=(100, 200, 400, 300),
    )
    engine.register_rule(rule)
    return engine


class TestHelmetViolation:
    def test_no_violation_for_non_two_wheeler(self, engine):
        result = engine.check_helmet_violation(
            tracker_id=1,
            has_helmet=False,
            vehicle_class="car",
            confidence=0.9,
            frame_id=1,
            bbox=[10, 20, 100, 200],
        )
        assert result is None

    def test_no_immediate_confirmation(self, engine):
        """Single frame should not confirm a violation."""
        result = engine.check_helmet_violation(
            tracker_id=1,
            has_helmet=False,
            vehicle_class="motorcycle",
            confidence=0.8,
            frame_id=1,
            bbox=[10, 20, 100, 200],
        )
        assert result is None

    def test_confirms_after_min_frames(self, engine):
        """Violation should be confirmed after min_frames consecutive detections."""
        for i in range(1, 4):  # 3 frames = min_frames
            result = engine.check_helmet_violation(
                tracker_id=1,
                has_helmet=False,
                vehicle_class="motorcycle",
                confidence=0.8,
                frame_id=i,
                bbox=[10, 20, 100, 200],
            )

        assert result is not None
        assert result["violation_type"] == ViolationType.HELMET_VIOLATION
        assert "avg_confidence" in result

    def test_no_duplicate_confirmation(self, engine):
        """Same tracker should not produce duplicate violations."""
        # Confirm the violation
        for i in range(1, 4):
            result = engine.check_helmet_violation(
                tracker_id=1,
                has_helmet=False,
                vehicle_class="motorcycle",
                confidence=0.8,
                frame_id=i,
                bbox=[10, 20, 100, 200],
            )
        assert result is not None

        # Subsequent frames should return None
        result = engine.check_helmet_violation(
            tracker_id=1,
            has_helmet=False,
            vehicle_class="motorcycle",
            confidence=0.8,
            frame_id=10,
            bbox=[10, 20, 100, 200],
        )
        assert result is None

    def test_resets_when_helmet_detected(self, engine):
        """If helmet is detected mid-way, candidate should reset."""
        # Two frames without helmet
        engine.check_helmet_violation(
            tracker_id=1, has_helmet=False, vehicle_class="motorcycle",
            confidence=0.8, frame_id=1, bbox=[10, 20, 100, 200],
        )
        engine.check_helmet_violation(
            tracker_id=1, has_helmet=False, vehicle_class="motorcycle",
            confidence=0.8, frame_id=2, bbox=[10, 20, 100, 200],
        )

        # Helmet detected — resets the counter
        engine.check_helmet_violation(
            tracker_id=1, has_helmet=True, vehicle_class="motorcycle",
            confidence=0.9, frame_id=3, bbox=[10, 20, 100, 200],
        )

        # Need 3 more frames to confirm now
        for i in range(4, 7):
            result = engine.check_helmet_violation(
                tracker_id=1, has_helmet=False, vehicle_class="motorcycle",
                confidence=0.8, frame_id=i, bbox=[10, 20, 100, 200],
            )

        assert result is not None

    def test_low_confidence_ignored(self, engine):
        """Detections below confidence threshold should be ignored."""
        for i in range(1, 10):
            result = engine.check_helmet_violation(
                tracker_id=1,
                has_helmet=False,
                vehicle_class="motorcycle",
                confidence=0.2,  # Below threshold of 0.3
                frame_id=i,
                bbox=[10, 20, 100, 200],
            )
        assert result is None

    def test_different_trackers_independent(self, engine):
        """Different tracker IDs should have independent violation candidates."""
        # Build up tracker 1
        for i in range(1, 3):
            engine.check_helmet_violation(
                tracker_id=1, has_helmet=False, vehicle_class="motorcycle",
                confidence=0.8, frame_id=i, bbox=[10, 20, 100, 200],
            )

        # Tracker 2 should start fresh
        engine.check_helmet_violation(
            tracker_id=2, has_helmet=False, vehicle_class="motorcycle",
            confidence=0.8, frame_id=1, bbox=[200, 200, 300, 400],
        )

        # Only tracker 1 should be close to confirmation
        result = engine.check_helmet_violation(
            tracker_id=1, has_helmet=False, vehicle_class="motorcycle",
            confidence=0.8, frame_id=3, bbox=[10, 20, 100, 200],
        )
        assert result is not None  # Confirmed for tracker 1

        # Tracker 2 needs 2 more
        result2 = engine.check_helmet_violation(
            tracker_id=2, has_helmet=False, vehicle_class="motorcycle",
            confidence=0.8, frame_id=2, bbox=[200, 200, 300, 400],
        )
        assert result2 is None  # Not yet confirmed


class TestWrongWayViolation:
    def test_wrong_way_detected(self, engine_with_rule):
        result = engine_with_rule.check_wrong_way(
            camera_id="cam-01", tracker_id=1, direction="up", frame_id=1
        )
        assert result is not None
        assert result["violation_type"] == ViolationType.WRONG_WAY

    def test_correct_direction_no_violation(self, engine_with_rule):
        result = engine_with_rule.check_wrong_way(
            camera_id="cam-01", tracker_id=1, direction="down", frame_id=1
        )
        assert result is None

    def test_no_rule_no_violation(self, engine):
        result = engine.check_wrong_way(
            camera_id="cam-unknown", tracker_id=1, direction="up", frame_id=1
        )
        assert result is None

    def test_no_direction_no_violation(self, engine_with_rule):
        result = engine_with_rule.check_wrong_way(
            camera_id="cam-01", tracker_id=1, direction=None, frame_id=1
        )
        assert result is None


class TestSignalJumpViolation:
    def test_signal_jump_detected(self, engine_with_rule):
        # Bbox center at (250, 250) which is inside signal_zone (100, 200, 400, 300)
        result = engine_with_rule.check_signal_jump(
            camera_id="cam-01", tracker_id=1, bbox=[200, 200, 300, 300], signal_state="red"
        )
        assert result is not None
        assert result["violation_type"] == ViolationType.SIGNAL_JUMP

    def test_green_signal_no_violation(self, engine_with_rule):
        result = engine_with_rule.check_signal_jump(
            camera_id="cam-01", tracker_id=1, bbox=[200, 200, 300, 300], signal_state="green"
        )
        assert result is None

    def test_outside_zone_no_violation(self, engine_with_rule):
        # Bbox center at (50, 50) which is outside signal_zone
        result = engine_with_rule.check_signal_jump(
            camera_id="cam-01", tracker_id=1, bbox=[0, 0, 100, 100], signal_state="red"
        )
        assert result is None


class TestReset:
    def test_reset_clears_all_state(self, engine):
        # Build up some candidates
        engine.check_helmet_violation(
            tracker_id=1, has_helmet=False, vehicle_class="motorcycle",
            confidence=0.8, frame_id=1, bbox=[10, 20, 100, 200],
        )
        engine.reset()

        assert len(engine._candidates) == 0
        assert len(engine._confirmed) == 0

    def test_reset_track(self, engine):
        engine.check_helmet_violation(
            tracker_id=1, has_helmet=False, vehicle_class="motorcycle",
            confidence=0.8, frame_id=1, bbox=[10, 20, 100, 200],
        )
        engine.reset_track(1)
        assert 1 not in engine._candidates
