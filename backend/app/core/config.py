import os
from pathlib import Path

from pydantic_settings import BaseSettings

# Project root: two levels up from this file (backend/app/core/config.py -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    APP_NAME: str = "Smart Traffic Violation Detection"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/traffic_violations"
    # Sync URL for Celery workers (non-async context)
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/traffic_violations"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Storage mode: "local" or "minio"
    STORAGE_MODE: str = "local"

    # Local storage paths (used when STORAGE_MODE=local)
    UPLOAD_DIR: str = str(PROJECT_ROOT / "data" / "uploads")
    CLIPS_DIR: str = str(PROJECT_ROOT / "data" / "clips")
    THUMBNAILS_DIR: str = str(PROJECT_ROOT / "data" / "thumbnails")
    EVIDENCE_DIR: str = str(PROJECT_ROOT / "data" / "evidence")

    # MinIO (used when STORAGE_MODE=minio)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_CLIPS: str = "violation-clips"
    MINIO_BUCKET_EVIDENCE: str = "evidence-packages"
    MINIO_SECURE: bool = False

    # ML Models
    DETECTION_MODEL_PATH: str = str(PROJECT_ROOT / "ml" / "models" / "yolov8n.pt")
    HELMET_MODEL_PATH: str = str(PROJECT_ROOT / "ml" / "models" / "helmet_detector.pt")
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.5
    HELMET_CONFIDENCE_THRESHOLD: float = 0.4
    OCR_LANG: str = "en"

    # Video processing
    MAX_CLIP_DURATION_SECONDS: int = 30
    FRAME_SKIP: int = 3
    CLIP_SECONDS_BEFORE: int = 3
    CLIP_SECONDS_AFTER: int = 3
    VIDEO_FPS: float = 30.0

    # Violation confirmation
    MIN_VIOLATION_FRAMES: int = 5  # frames needed to confirm a violation

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    def ensure_dirs(self):
        """Create local storage directories if they don't exist."""
        for d in [self.UPLOAD_DIR, self.CLIPS_DIR, self.THUMBNAILS_DIR, self.EVIDENCE_DIR]:
            os.makedirs(d, exist_ok=True)


settings = Settings()
