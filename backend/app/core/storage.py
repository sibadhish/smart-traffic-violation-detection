"""
Storage abstraction layer.

Supports two modes:
- "local": stores files on local filesystem (default, no external deps)
- "minio": stores files in MinIO S3-compatible storage
"""

import io
import os
import shutil
from pathlib import Path

from backend.app.core.config import settings


class LocalStorage:
    """File storage using the local filesystem."""

    def save_file(self, data: bytes | io.BytesIO, directory: str, filename: str) -> str:
        """Save bytes or BytesIO to a file. Returns the relative path."""
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, filename)
        if isinstance(data, io.BytesIO):
            data.seek(0)
            with open(filepath, "wb") as f:
                f.write(data.read())
        else:
            with open(filepath, "wb") as f:
                f.write(data)
        return filepath

    def save_uploaded_file(self, source_path: str, directory: str, filename: str) -> str:
        """Copy a file from source to storage directory. Returns destination path."""
        os.makedirs(directory, exist_ok=True)
        dest = os.path.join(directory, filename)
        shutil.copy2(source_path, dest)
        return dest

    def get_file_path(self, directory: str, filename: str) -> str | None:
        """Return absolute path if file exists, else None."""
        filepath = os.path.join(directory, filename)
        return filepath if os.path.exists(filepath) else None

    def delete_file(self, filepath: str) -> bool:
        """Delete a file. Returns True if deleted."""
        try:
            os.remove(filepath)
            return True
        except FileNotFoundError:
            return False


class MinIOStorage:
    """File storage using MinIO S3-compatible object store."""

    def __init__(self):
        from minio import Minio
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def ensure_buckets(self):
        for bucket in [settings.MINIO_BUCKET_CLIPS, settings.MINIO_BUCKET_EVIDENCE]:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)

    def save_file(self, data: bytes | io.BytesIO, bucket: str, object_name: str) -> str:
        if isinstance(data, bytes):
            data = io.BytesIO(data)
        data.seek(0)
        length = data.getbuffer().nbytes if hasattr(data, "getbuffer") else -1
        self.client.put_object(bucket, object_name, data, length=length)
        return f"{bucket}/{object_name}"

    def fput_file(self, bucket: str, object_name: str, file_path: str) -> str:
        self.client.fput_object(bucket, object_name, file_path)
        return f"{bucket}/{object_name}"


def get_storage() -> LocalStorage | MinIOStorage:
    """Return the configured storage backend."""
    if settings.STORAGE_MODE == "minio":
        return MinIOStorage()
    return LocalStorage()


def ensure_buckets():
    """Initialize storage (create dirs or MinIO buckets)."""
    if settings.STORAGE_MODE == "minio":
        storage = MinIOStorage()
        storage.ensure_buckets()
    else:
        settings.ensure_dirs()
