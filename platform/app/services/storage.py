from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from app.core.settings import Settings


@dataclass(frozen=True)
class StoredFile:
    path: str


class ImageStorage(Protocol):
    def save_image(self, upload_file: UploadFile, device_id: int, suffix: str) -> StoredFile:
        ...


class LocalImageStorage:
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir

    def save_image(self, upload_file: UploadFile, device_id: int, suffix: str) -> StoredFile:
        target_dir = Path(self.upload_dir) / f"device-{device_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / image_filename(suffix)

        with target_path.open("wb") as handle:
            while chunk := upload_file.file.read(1024 * 1024):
                handle.write(chunk)

        return StoredFile(path=str(target_path))


class GcsImageStorage:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    def save_image(self, upload_file: UploadFile, device_id: int, suffix: str) -> StoredFile:
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("google-cloud-storage is required when PLANTLAB_STORAGE_BACKEND=gcs.") from exc

        object_name = f"device-{device_id}/{image_filename(suffix)}"
        client = storage.Client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_file(upload_file.file, content_type=upload_file.content_type)
        return StoredFile(path=blob.public_url)


def get_image_storage(settings: Settings) -> ImageStorage:
    if settings.storage_backend == "local":
        return LocalImageStorage(settings.upload_dir)
    if settings.storage_backend == "gcs":
        if not settings.gcs_bucket_name:
            raise RuntimeError("GCS_BUCKET_NAME is required when PLANTLAB_STORAGE_BACKEND=gcs.")
        return GcsImageStorage(settings.gcs_bucket_name)
    raise RuntimeError(f"Unsupported PLANTLAB_STORAGE_BACKEND: {settings.storage_backend}")


def image_filename(suffix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    return f"{timestamp}_{uuid4().hex}{suffix}"


def image_src(path: str) -> str:
    if path.startswith(("http://", "https://", "/")):
        return path
    return f"/{path}"
