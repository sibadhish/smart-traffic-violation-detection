"""Tests for the detection module utilities."""

import pytest

from backend.app.services.detection.detector import find_rider_for_motorcycle


class TestFindRiderForMotorcycle:
    def test_finds_overlapping_person(self):
        motorcycle_bbox = [100, 100, 300, 400]
        persons = [
            {"bbox": [120, 80, 280, 350], "confidence": 0.9, "class_id": 0},
        ]
        result = find_rider_for_motorcycle(motorcycle_bbox, persons)
        assert result is not None
        assert result["bbox"] == [120, 80, 280, 350]

    def test_returns_none_for_no_overlap(self):
        motorcycle_bbox = [100, 100, 300, 400]
        persons = [
            {"bbox": [500, 500, 600, 600], "confidence": 0.9, "class_id": 0},
        ]
        result = find_rider_for_motorcycle(motorcycle_bbox, persons)
        assert result is None

    def test_returns_best_overlap(self):
        motorcycle_bbox = [100, 100, 300, 400]
        persons = [
            {"bbox": [250, 250, 350, 450], "confidence": 0.8, "class_id": 0},  # less overlap
            {"bbox": [120, 80, 280, 380], "confidence": 0.9, "class_id": 0},   # more overlap
        ]
        result = find_rider_for_motorcycle(motorcycle_bbox, persons)
        assert result is not None
        assert result["bbox"] == [120, 80, 280, 380]

    def test_empty_persons_list(self):
        motorcycle_bbox = [100, 100, 300, 400]
        result = find_rider_for_motorcycle(motorcycle_bbox, [])
        assert result is None

    def test_below_iou_threshold(self):
        motorcycle_bbox = [100, 100, 300, 400]
        persons = [
            {"bbox": [290, 390, 310, 410], "confidence": 0.9, "class_id": 0},  # tiny overlap
        ]
        result = find_rider_for_motorcycle(motorcycle_bbox, persons, iou_threshold=0.5)
        assert result is None
