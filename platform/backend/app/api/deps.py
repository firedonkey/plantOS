from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.core.settings import get_settings
from app.models import Device, User
from app.services.devices import get_device_by_api_token
from app.services.dev_auth import read_dev_token
from app.services.standalone_auth import get_user_from_access_token
from app.services.users import get_user_by_id


def get_optional_current_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    authorization = str(request.headers.get("Authorization") or "").strip()
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if not token:
            return None
        settings = get_settings()
        user = get_user_from_access_token(settings, session, token)
        if user is not None:
            return user
        if not settings.dev_token_auth_enabled:
            return None
        user_id = read_dev_token(settings, token)
        if user_id is None:
            return None
        return get_user_by_id(session, user_id)

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


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    settings = get_settings()
    if (current_user.email or "").strip().lower() not in settings.effective_admin_emails:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def get_device_from_token(request: Request, session: Session) -> Device | None:
    api_token = request.headers.get("X-Device-Token")
    if not api_token:
        return None
    return get_device_by_api_token(session, api_token)
