"""
Video ingestion service.

Supports:
- File uploads (MP4, AVI, MKV, MOV)
- RTSP / HTTP live camera streams
- Frame extraction with configurable skip
"""

import logging
from pathlib import Path
from typing import Generator

import cv2
import numpy as np

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}


class VideoIngest:
    """Reads frames from a video file or live stream."""

    def __init__(self, source: str, frame_skip: int | None = None):
        """
        Args:
            source: file path or RTSP/HTTP URL
            frame_skip: process every Nth frame (default from settings)
        """
        self.source = source
        self.frame_skip = frame_skip or settings.FRAME_SKIP
        self.cap: cv2.VideoCapture | None = None
        self._fps: float = 0.0
        self._total_frames: int = 0
        self._width: int = 0
        self._height: int = 0

    def open(self) -> bool:
        """Open the video source. Returns True on success."""
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            logger.error(f"Failed to open video source: {self.source}")
            return False

        self._fps = self.cap.get(cv2.CAP_PROP_FPS) or settings.VIDEO_FPS
        self._total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(
            f"Opened {self.source}: {self._width}x{self._height} @ {self._fps:.1f}fps, "
            f"total_frames={self._total_frames}"
        )
        return True

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def resolution(self) -> tuple[int, int]:
        return self._width, self._height

    @property
    def is_live(self) -> bool:
        """True if source is a live stream (RTSP/HTTP)."""
        return self.source.startswith(("rtsp://", "http://", "https://"))

    def frames(self) -> Generator[tuple[int, np.ndarray], None, None]:
        """
        Yield (frame_number, frame) tuples, respecting frame_skip.

        For a file, iterates until EOF. For a stream, runs indefinitely.
        """
        if self.cap is None or not self.cap.isOpened():
            if not self.open():
                return

        frame_count = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % self.frame_skip != 0:
                continue

            yield frame_count, frame

    def release(self):
        """Release the video capture."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.release()


def validate_video_file(filepath: str) -> bool:
    """Check if a file is a valid, openable video."""
    ext = Path(filepath).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return False

    cap = cv2.VideoCapture(filepath)
    valid = cap.isOpened()
    if valid:
        ret, _ = cap.read()
        valid = ret
    cap.release()
    return valid
