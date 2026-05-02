"""
Celery tasks for async video processing and evidence generation.

These run in a synchronous context (Celery workers), so they use
the sync database session rather than the async FastAPI one.
"""

import json
import logging
import uuid
from datetime import datetime

import cv2

from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.models.violation import Violation, ViolationStatus, ViolationType
from backend.app.services.violations.evidence import EvidenceGenerator
from backend.app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_video_feed")
def process_video_feed(self, camera_id: str, stream_url: str):
    """
    Process a video file or stream for traffic violations.

    This is the main processing task. It:
    1. Opens the video source
    2. Runs each frame through the detection pipeline
    3. On confirmed violations, saves to DB and generates evidence
    """
    from backend.app.services.pipeline import TrafficPipeline
    from backend.app.services.violations.rule_engine import ViolationRuleEngine

    logger.info(f"Starting processing: camera={camera_id}, source={stream_url}")

    rule_engine = ViolationRuleEngine()
    pipeline = TrafficPipeline(camera_id, rule_engine)
    evidence_gen = EvidenceGenerator()

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {stream_url}")

    fps = cap.get(cv2.CAP_PROP_FPS) or settings.VIDEO_FPS
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_count = 0
    violations_found = 0

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % settings.FRAME_SKIP != 0:
                continue

            # Run detection pipeline
            violations = pipeline.process_frame(frame)

            for violation_data in violations:
                violations_found += 1
                violation_id = str(uuid.uuid4())

                # Save evidence (clip + thumbnail)
                try:
                    clip_frames = pipeline.get_clip_frames(violation_data["frame_id"])
                    clip_url = ""
                    thumbnail_url = ""

                    if clip_frames:
                        clip_url = evidence_gen.save_clip(clip_frames, fps, violation_id)

                    # Save thumbnail from the violation frame
                    violation_frame = pipeline.get_frame_at(violation_data["frame_id"])
                    if violation_frame is not None:
                        thumbnail_url = evidence_gen.save_thumbnail(
                            violation_frame, violation_id, violation_data.get("bbox")
                        )

                    # Generate evidence package
                    evidence_url = evidence_gen.generate_evidence_package(
                        violation_id=violation_id,
                        violation_data=violation_data,
                        clip_url=clip_url,
                        thumbnail_url=thumbnail_url,
                    )
                except Exception as e:
                    logger.error(f"Evidence generation failed for {violation_id}: {e}")
                    clip_url = ""
                    thumbnail_url = ""
                    evidence_url = ""

                # Persist to database
                try:
                    _save_violation_to_db(
                        violation_id=violation_id,
                        camera_id=camera_id,
                        violation_data=violation_data,
                        clip_url=clip_url,
                        thumbnail_url=thumbnail_url,
                        evidence_url=evidence_url,
                    )
                except Exception as e:
                    logger.error(f"DB save failed for {violation_id}: {e}")

            # Update task progress
            self.update_state(
                state="PROCESSING",
                meta={
                    "frames_processed": frame_count,
                    "total_frames": total_frames,
                    "violations_found": violations_found,
                    "camera_id": camera_id,
                    "progress_pct": (frame_count / total_frames * 100) if total_frames > 0 else 0,
                },
            )

    finally:
        cap.release()

    logger.info(
        f"Processing complete: camera={camera_id}, frames={frame_count}, "
        f"violations={violations_found}"
    )

    return {
        "frames_processed": frame_count,
        "violations_found": violations_found,
        "camera_id": camera_id,
    }


def _save_violation_to_db(
    violation_id: str,
    camera_id: str,
    violation_data: dict,
    clip_url: str,
    thumbnail_url: str,
    evidence_url: str,
):
    """Save a violation record to the database (sync context)."""
    session = SyncSessionLocal()
    try:
        # Map string violation type to enum
        vtype_str = violation_data.get("violation_type", "")
        if isinstance(vtype_str, ViolationType):
            vtype = vtype_str
        else:
            vtype = ViolationType(str(vtype_str))

        violation = Violation(
            id=uuid.UUID(violation_id),
            camera_id=camera_id,
            violation_type=vtype,
            status=ViolationStatus.DETECTED,
            license_plate=violation_data.get("license_plate"),
            confidence=float(violation_data.get("confidence", 0.0)),
            clip_url=clip_url,
            thumbnail_url=thumbnail_url,
            evidence_package_url=evidence_url,
            detected_at=datetime.utcnow(),
            metadata_json=json.dumps({
                "tracker_id": violation_data.get("tracker_id"),
                "frame_id": violation_data.get("frame_id"),
                "bbox": violation_data.get("bbox"),
                "details": violation_data.get("details"),
                "frame_count": violation_data.get("frame_count"),
            }, default=str),
        )

        session.add(violation)
        session.commit()
        logger.info(f"Violation saved to DB: {violation_id} ({vtype.value})")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@celery_app.task(name="generate_evidence")
def generate_evidence(violation_id: str, camera_id: str, violation_data: dict):
    """
    Generate evidence package for an existing violation.

    This task can be called separately to regenerate evidence.
    """
    evidence_gen = EvidenceGenerator()

    evidence_url = evidence_gen.generate_evidence_package(
        violation_id=violation_id,
        violation_data={
            "camera_id": camera_id,
            **violation_data,
        },
        clip_url=violation_data.get("clip_url", ""),
        thumbnail_url=violation_data.get("thumbnail_url", ""),
    )

    # Update the violation record with the evidence URL
    session = SyncSessionLocal()
    try:
        violation = session.query(Violation).filter(
            Violation.id == uuid.UUID(violation_id)
        ).first()
        if violation:
            violation.evidence_package_url = evidence_url
            violation.status = ViolationStatus.EVIDENCE_GENERATED
            violation.updated_at = datetime.utcnow()
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return {"violation_id": violation_id, "status": "evidence_generated"}
