from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.models import Image
from app.services.storage import get_image_storage


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_uploaded_image(
    *,
    session: Session,
    upload_file: UploadFile,
    device_id: int,
    source_hardware_device_id: str | None,
    settings: Settings,
    captured_at: datetime | None = None,
) -> Image:
    suffix = ALLOWED_IMAGE_TYPES.get(upload_file.content_type or "")
    if suffix is None:
        raise ValueError("Unsupported image type.")

    stored_file = get_image_storage(settings).save_image(upload_file, device_id, suffix)
    image = Image(
        device_id=device_id,
        source_hardware_device_id=source_hardware_device_id,
        path=stored_file.path,
        timestamp=captured_at or datetime.now(timezone.utc),
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


def list_recent_images_for_device(
    session: Session,
    device_id: int,
    limit: int = 12,
) -> list[Image]:
    return list(
        session.scalars(
            select(Image)
            .where(Image.device_id == device_id)
            .order_by(Image.timestamp.desc())
            .limit(limit)
        )
    )


def list_timelapse_images_for_device(
    session: Session,
    device_id: int,
    *,
    start: datetime,
    end: datetime,
    interval_minutes: int,
    max_frames: int,
) -> tuple[list[Image], int]:
    images = list(
        session.scalars(
            select(Image)
            .where(Image.device_id == device_id)
            .where(Image.timestamp >= start)
            .where(Image.timestamp <= end)
            .order_by(Image.timestamp.asc(), Image.id.asc())
        )
    )
    if not images:
        return [], 0

    interval_seconds = max(interval_minutes * 60, 1)
    start_utc = _as_utc(start)
    bucketed: list[Image] = []
    seen_buckets: set[int] = set()
    for image in images:
        elapsed_seconds = max(0, (_as_utc(image.timestamp) - start_utc).total_seconds())
        bucket = int(elapsed_seconds // interval_seconds)
        if bucket in seen_buckets:
            continue
        seen_buckets.add(bucket)
        bucketed.append(image)

    if len(bucketed) <= max_frames:
        return bucketed, len(images)

    return _downsample_images(bucketed, max_frames), len(images)


def _downsample_images(images: list[Image], max_frames: int) -> list[Image]:
    if max_frames <= 1:
        return images[:1]
    if len(images) <= max_frames:
        return images

    step = (len(images) - 1) / (max_frames - 1)
    selected_indexes = {round(index * step) for index in range(max_frames)}
    return [image for index, image in enumerate(images) if index in selected_indexes][:max_frames]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
