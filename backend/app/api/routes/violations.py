import json
import os
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.violation import Violation, ViolationStatus, ViolationType
from backend.app.schemas.violation import (
    ViolationResponse,
    ViolationStats,
    ViolationUpdate,
)

router = APIRouter(prefix="/violations", tags=["violations"])


@router.get("/", response_model=list[ViolationResponse])
async def list_violations(
    camera_id: str | None = None,
    violation_type: ViolationType | None = None,
    status: ViolationStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Violation).order_by(Violation.detected_at.desc())

    if camera_id:
        query = query.where(Violation.camera_id == camera_id)
    if violation_type:
        query = query.where(Violation.violation_type == violation_type)
    if status:
        query = query.where(Violation.status == status)
    if date_from:
        query = query.where(Violation.detected_at >= date_from)
    if date_to:
        query = query.where(Violation.detected_at <= date_to)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats", response_model=ViolationStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(Violation.id)))

    type_query = await db.execute(
        select(Violation.violation_type, func.count(Violation.id))
        .group_by(Violation.violation_type)
    )
    by_type = {str(row[0].value): row[1] for row in type_query.all()}

    status_query = await db.execute(
        select(Violation.status, func.count(Violation.id))
        .group_by(Violation.status)
    )
    by_status = {str(row[0].value): row[1] for row in status_query.all()}

    camera_query = await db.execute(
        select(Violation.camera_id, func.count(Violation.id))
        .group_by(Violation.camera_id)
    )
    by_camera = {row[0]: row[1] for row in camera_query.all()}

    now = datetime.utcnow()
    today_count = await db.scalar(
        select(func.count(Violation.id)).where(
            Violation.detected_at >= now.replace(hour=0, minute=0, second=0)
        )
    )
    week_count = await db.scalar(
        select(func.count(Violation.id)).where(
            Violation.detected_at >= now - timedelta(days=7)
        )
    )

    return ViolationStats(
        total_violations=total or 0,
        by_type=by_type,
        by_status=by_status,
        by_camera=by_camera,
        today_count=today_count or 0,
        this_week_count=week_count or 0,
    )


@router.get("/{violation_id}", response_model=ViolationResponse)
async def get_violation(violation_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Violation).where(Violation.id == violation_id)
    )
    violation = result.scalar_one_or_none()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    return violation


@router.patch("/{violation_id}", response_model=ViolationResponse)
async def update_violation(
    violation_id: UUID,
    update: ViolationUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Violation).where(Violation.id == violation_id)
    )
    violation = result.scalar_one_or_none()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(violation, field, value)

    violation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(violation)
    return violation


@router.get("/{violation_id}/evidence")
async def download_evidence(
    violation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Download evidence bundle (ZIP) for a violation."""
    result = await db.execute(
        select(Violation).where(Violation.id == violation_id)
    )
    violation = result.scalar_one_or_none()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    from backend.app.services.violations.pdf_report import generate_evidence_bundle

    # Gather paths
    vid = str(violation.id)
    clip_path = os.path.join(settings.CLIPS_DIR, f"{vid}.mp4")
    thumbnail_path = os.path.join(settings.THUMBNAILS_DIR, f"{vid}.jpg")

    violation_data = {
        "violation_type": violation.violation_type.value if violation.violation_type else "",
        "camera_id": violation.camera_id,
        "license_plate": violation.license_plate or "",
        "confidence": violation.confidence,
        "detected_at": violation.detected_at.isoformat() if violation.detected_at else "",
        "details": "",
    }

    # Parse metadata_json for additional details
    if violation.metadata_json:
        try:
            meta = json.loads(violation.metadata_json)
            violation_data["details"] = meta.get("details", "")
            violation_data["bbox"] = meta.get("bbox")
            violation_data["frame_id"] = meta.get("frame_id")
            violation_data["tracker_id"] = meta.get("tracker_id")
        except json.JSONDecodeError:
            pass

    zip_path = generate_evidence_bundle(
        violation_id=vid,
        violation_data=violation_data,
        clip_path=clip_path if os.path.exists(clip_path) else None,
        thumbnail_path=thumbnail_path if os.path.exists(thumbnail_path) else None,
    )

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"evidence_{vid}.zip",
    )
