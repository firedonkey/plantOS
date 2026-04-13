from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from platform_app.db.session import get_session
from platform_app.models import User
from platform_app.services.users import get_user_by_id


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required.")

    user = get_user_by_id(session, int(user_id))
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Sign in required.")

    return user
