"""
Processing API routes.

Endpoints for uploading videos and starting stream processing.
"""

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.violation import Camera

router = APIRouter(prefix="/process", tags=["processing"])


class ProcessingResponse(BaseModel):
    task_id: str
    status: str
    message: str


class StreamRequest(BaseModel):
    camera_id: str


class UploadResponse(BaseModel):
    task_id: str
    filename: str
    status: str
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a video file for violation detection processing."""
    # Validate file type
    allowed_types = {
        "video/mp4", "video/avi", "video/x-msvideo",
        "video/quicktime", "video/x-matroska", "video/webm",
    }
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Upload MP4, AVI, MOV, MKV, or WebM.",
        )

    # Save uploaded file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    filename = f"{file_id}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    with open(filepath, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)

    # Dispatch Celery task
    from backend.app.workers.tasks import process_video_feed
    task = process_video_feed.delay(
        camera_id=f"upload-{file_id[:8]}",
        stream_url=filepath,
    )

    return UploadResponse(
        task_id=task.id,
        filename=file.filename or filename,
        status="queued",
        message="Video uploaded and queued for processing.",
    )


@router.post("/stream", response_model=ProcessingResponse)
async def start_stream_processing(
    request: StreamRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start processing a live camera stream."""
    # Look up camera
    result = await db.execute(
        select(Camera).where(Camera.id == request.camera_id)
    )
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    if camera.status != "active":
        raise HTTPException(status_code=400, detail="Camera is not active")

    # Dispatch Celery task
    from backend.app.workers.tasks import process_video_feed
    task = process_video_feed.delay(
        camera_id=camera.id,
        stream_url=camera.stream_url,
    )

    return ProcessingResponse(
        task_id=task.id,
        status="started",
        message=f"Started processing stream for camera {camera.name}",
    )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a processing task."""
    from backend.app.workers.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.status == "PROCESSING":
        response["meta"] = result.info
    elif result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        response["error"] = str(result.result)

    return response
