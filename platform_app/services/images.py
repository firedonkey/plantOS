from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from platform_app.models import Image


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
    upload_dir: str,
) -> Image:
    suffix = ALLOWED_IMAGE_TYPES.get(upload_file.content_type or "")
    if suffix is None:
        raise ValueError("Unsupported image type.")

    target_dir = Path(upload_dir) / f"device-{device_id}"
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}_{uuid4().hex}{suffix}"
    target_path = target_dir / filename

    with target_path.open("wb") as handle:
        while chunk := upload_file.file.read(1024 * 1024):
            handle.write(chunk)

    image = Image(device_id=device_id, path=str(target_path))
    session.add(image)
    session.commit()
    session.refresh(image)
    return image
