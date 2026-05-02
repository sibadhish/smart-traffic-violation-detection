"""
Video clip extraction for violation evidence.

Extracts short video clips around violation events using OpenCV.
Falls back to FFmpeg subprocess if available for better codec support.
"""

import logging
import os
import subprocess
import tempfile

import cv2
import numpy as np

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class ClipExtractor:
    """Extracts video clips from buffered frames or source video files."""

    def extract_from_frames(
        self,
        frames: list[np.ndarray],
        output_path: str,
        fps: float | None = None,
    ) -> str:
        """
        Write a list of frames to an MP4 file.

        Args:
            frames: list of BGR numpy frames
            output_path: where to save the clip
            fps: frames per second (default from settings)

        Returns:
            Path to the written clip file.
        """
        if not frames:
            raise ValueError("No frames to extract")

        fps = fps or settings.VIDEO_FPS
        h, w = frames[0].shape[:2]

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Write with OpenCV first to a temp file, then convert with ffmpeg if available
        tmp_path = output_path + ".tmp.avi"
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (w, h))

        for frame in frames:
            writer.write(frame)
        writer.release()

        # Try converting to proper MP4 with ffmpeg
        if self._ffmpeg_available():
            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", tmp_path,
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        output_path,
                    ],
                    capture_output=True,
                    timeout=60,
                    check=True,
                )
                os.remove(tmp_path)
                logger.info(f"Clip saved (ffmpeg): {output_path}")
                return output_path
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.warning(f"FFmpeg conversion failed, using raw AVI: {e}")

        # Fallback: just rename the AVI
        os.rename(tmp_path, output_path)
        logger.info(f"Clip saved (raw): {output_path}")
        return output_path

    def extract_from_video(
        self,
        source_path: str,
        output_path: str,
        start_frame: int,
        end_frame: int,
        fps: float | None = None,
    ) -> str:
        """
        Extract a clip from a source video file by frame range.

        If ffmpeg is available, uses time-based seeking for efficiency.
        Otherwise falls back to frame-by-frame extraction with OpenCV.
        """
        fps = fps or settings.VIDEO_FPS
        start_time = start_frame / fps
        duration = (end_frame - start_frame) / fps

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self._ffmpeg_available():
            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-ss", f"{start_time:.3f}",
                        "-i", source_path,
                        "-t", f"{duration:.3f}",
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        output_path,
                    ],
                    capture_output=True,
                    timeout=120,
                    check=True,
                )
                logger.info(f"Clip extracted (ffmpeg): {output_path}")
                return output_path
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.warning(f"FFmpeg extraction failed, falling back to OpenCV: {e}")

        # Fallback: read frames with OpenCV
        cap = cv2.VideoCapture(source_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frames = []
        for _ in range(end_frame - start_frame):
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()

        if frames:
            return self.extract_from_frames(frames, output_path, fps)
        raise RuntimeError(f"No frames read from {source_path}")

    def save_thumbnail(
        self,
        frame: np.ndarray,
        output_path: str,
        bbox: list[float] | None = None,
    ) -> str:
        """
        Save an annotated thumbnail image.

        If bbox is provided, draws a red rectangle around the violation area.
        """
        annotated = frame.copy()

        if bbox:
            x1, y1, x2, y2 = [int(c) for c in bbox]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
            # Add label
            cv2.putText(
                annotated, "VIOLATION",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        logger.info(f"Thumbnail saved: {output_path}")
        return output_path

    @staticmethod
    def _ffmpeg_available() -> bool:
        """Check if ffmpeg is installed."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
