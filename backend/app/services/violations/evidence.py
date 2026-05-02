"""
Evidence package generator.

Creates evidence packages for confirmed violations:
- Video clip around the violation
- Annotated thumbnail image
- JSON metadata
- (Phase 4) PDF report + ZIP bundle
"""

import io
import json
import logging
import os
from datetime import datetime

import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.services.clip_extractor import ClipExtractor

logger = logging.getLogger(__name__)


class EvidenceGenerator:
    """Generates evidence packages for traffic violations."""

    def __init__(self):
        self.clip_extractor = ClipExtractor()

    def save_clip(
        self,
        frames: list[np.ndarray],
        fps: float,
        violation_id: str,
    ) -> str:
        """
        Save a violation clip from buffered frames.

        Returns: path/URL to the saved clip.
        """
        filename = f"{violation_id}.mp4"
        output_path = os.path.join(settings.CLIPS_DIR, filename)
        self.clip_extractor.extract_from_frames(frames, output_path, fps)
        return f"/static/clips/{filename}"

    def save_clip_from_video(
        self,
        source_path: str,
        violation_id: str,
        start_frame: int,
        end_frame: int,
        fps: float,
    ) -> str:
        """
        Extract a violation clip from the source video file.

        Returns: URL path to the saved clip.
        """
        filename = f"{violation_id}.mp4"
        output_path = os.path.join(settings.CLIPS_DIR, filename)
        self.clip_extractor.extract_from_video(
            source_path, output_path, start_frame, end_frame, fps
        )
        return f"/static/clips/{filename}"

    def save_thumbnail(
        self,
        frame: np.ndarray,
        violation_id: str,
        bbox: list[float] | None = None,
    ) -> str:
        """
        Save an annotated thumbnail for the violation.

        Returns: URL path to the saved thumbnail.
        """
        filename = f"{violation_id}.jpg"
        output_path = os.path.join(settings.THUMBNAILS_DIR, filename)
        self.clip_extractor.save_thumbnail(frame, output_path, bbox)
        return f"/static/thumbnails/{filename}"

    def generate_evidence_package(
        self,
        violation_id: str,
        violation_data: dict,
        clip_url: str,
        thumbnail_url: str,
    ) -> str:
        """
        Create a JSON evidence package with all violation metadata.

        Returns: URL path to the saved package.
        """
        package = {
            "violation_id": violation_id,
            "generated_at": datetime.utcnow().isoformat(),
            "violation": {
                "type": violation_data.get("violation_type", ""),
                "details": violation_data.get("details", ""),
                "confidence": violation_data.get("confidence", 0.0),
                "license_plate": violation_data.get("license_plate", ""),
                "camera_id": violation_data.get("camera_id", ""),
                "frame_id": violation_data.get("frame_id", 0),
                "bbox": violation_data.get("bbox", []),
            },
            "evidence_files": {
                "video_clip": clip_url,
                "thumbnail": thumbnail_url,
            },
        }

        filename = f"{violation_id}.json"
        output_path = os.path.join(settings.EVIDENCE_DIR, filename)
        os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(package, f, indent=2, default=str)

        logger.info(f"Evidence package saved: {output_path}")
        return f"/static/evidence/{filename}"
