from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device_from_token, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.models import Device, Image, User
from app.schemas.images import ImageRead
from app.services.devices import get_device_for_user
from app.services.images import save_uploaded_image
from app.services.storage import image_response


router = APIRouter(prefix="/api", tags=["images"])


@router.post("/image", response_model=ImageRead, status_code=201)
def upload_image(
    request: Request,
    device_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user is not None:
        device = get_device_for_user(session, current_user, device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found.")
    else:
        device = get_device_from_token(request, session)
        if device is None:
            raise HTTPException(status_code=401, detail="Sign in or valid device token required.")
        if device.id != device_id:
            raise HTTPException(status_code=403, detail="Device token does not match device_id.")

    try:
        return save_uploaded_image(
            session=session,
            upload_file=file,
            device_id=device.id,
            settings=get_settings(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/images/{image_id}/content")
def image_content(
    image_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    image = session.scalars(
        select(Image)
        .join(Device)
        .where(Image.id == image_id)
        .where(Device.user_id == current_user.id)
    ).first()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found.")

    try:
        return image_response(image.path, get_settings())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Image content not found.") from exc
