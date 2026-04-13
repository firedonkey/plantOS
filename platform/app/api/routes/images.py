from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.models import User
from app.schemas.images import ImageRead
from app.services.devices import get_device_for_user
from app.services.images import save_uploaded_image


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
            upload_dir=get_settings().upload_dir,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
