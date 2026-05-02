from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.violation import Camera
from backend.app.schemas.violation import CameraCreate, CameraResponse

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("/", response_model=list[CameraResponse])
async def list_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).order_by(Camera.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=CameraResponse, status_code=201)
async def create_camera(camera: CameraCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Camera).where(Camera.id == camera.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Camera ID already exists")

    db_camera = Camera(**camera.model_dump())
    db.add(db_camera)
    await db.commit()
    await db.refresh(db_camera)
    return db_camera


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    await db.delete(camera)
    await db.commit()
