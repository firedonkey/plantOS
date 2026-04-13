from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import Device, User
from app.services.devices import get_device_by_api_token
from app.services.users import get_user_by_id


def get_optional_current_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    user = get_user_by_id(session, int(user_id))
    if user is None:
        request.session.clear()
        return None

    return user


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    user = get_optional_current_user(request, session)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required.")

    return user


def get_device_from_token(request: Request, session: Session) -> Device | None:
    api_token = request.headers.get("X-Device-Token")
    if not api_token:
        return None
    return get_device_by_api_token(session, api_token)
