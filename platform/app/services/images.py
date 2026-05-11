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
) -> Image:
    suffix = ALLOWED_IMAGE_TYPES.get(upload_file.content_type or "")
    if suffix is None:
        raise ValueError("Unsupported image type.")

    stored_file = get_image_storage(settings).save_image(upload_file, device_id, suffix)
    image = Image(
        device_id=device_id,
        source_hardware_device_id=source_hardware_device_id,
        path=stored_file.path,
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
