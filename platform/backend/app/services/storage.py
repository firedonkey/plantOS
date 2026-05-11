from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from mimetypes import guess_type
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlparse
from uuid import uuid4

from fastapi import UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse

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


def proxied_image_src(image_id: int) -> str:
    return f"/api/images/{image_id}/content"


def image_response(path: str, settings: Settings) -> Response:
    if settings.storage_backend == "gcs" or _is_gcs_url(path):
        bucket_name, object_name = _gcs_object_from_path(path, settings)
        return _gcs_image_response(bucket_name, object_name)

    media_type, _ = guess_type(path)
    return FileResponse(path, media_type=media_type or "application/octet-stream")


def _gcs_image_response(bucket_name: str, object_name: str) -> Response:
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise RuntimeError("google-cloud-storage is required for GCS image reads.") from exc

    client = storage.Client()
    blob = client.bucket(bucket_name).blob(object_name)
    try:
        data = blob.download_as_bytes()
    except Exception as exc:
        raise RuntimeError("GCS image could not be read.") from exc
    media_type = blob.content_type or guess_type(object_name)[0] or "application/octet-stream"
    return StreamingResponse(BytesIO(data), media_type=media_type)


def _is_gcs_url(path: str) -> bool:
    return path.startswith("gs://") or "storage.googleapis.com/" in path


def _gcs_object_from_path(path: str, settings: Settings) -> tuple[str, str]:
    if path.startswith("gs://"):
        parsed = urlparse(path)
        return parsed.netloc, unquote(parsed.path.lstrip("/"))

    parsed = urlparse(path)
    if parsed.netloc == "storage.googleapis.com":
        parts = parsed.path.lstrip("/").split("/", 1)
        if len(parts) != 2:
            raise ValueError("GCS image URL is missing bucket or object path.")
        return parts[0], unquote(parts[1])

    if not settings.gcs_bucket_name:
        raise ValueError("GCS_BUCKET_NAME is required to read GCS image paths.")
    return settings.gcs_bucket_name, path.lstrip("/")
