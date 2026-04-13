from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def upsert_google_user(
    session: Session,
    *,
    google_sub: str,
    email: str,
    name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    user = session.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        user = session.scalar(select(User).where(User.email == email))

    if user is None:
        user = User(email=email, google_sub=google_sub)
        session.add(user)

    user.name = name
    user.avatar_url = avatar_url
    user.google_sub = google_sub
    session.commit()
    session.refresh(user)
    return user
