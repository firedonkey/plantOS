from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import AuthHandoffCode, AuthRefreshSession, Device, User
from app.services.devices import _delete_device_record


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_or_create_local_dev_user(session: Session, *, email: str) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        default_name = email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip().title() or "PlantLab User"
        user = User(email=email, name=default_name)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


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


def upsert_apple_user(
    session: Session,
    *,
    apple_sub: str,
    email: str | None = None,
    name: str | None = None,
) -> User | None:
    user = session.scalar(select(User).where(User.apple_sub == apple_sub))
    if user is None and email:
        user = session.scalar(select(User).where(User.email == email))

    if user is None:
        if not email:
            return None
        user = User(email=email, apple_sub=apple_sub)
        session.add(user)

    if name:
        user.name = name
    user.apple_sub = apple_sub
    session.commit()
    session.refresh(user)
    return user


def delete_user_account(session: Session, user: User) -> None:
    devices = list(session.scalars(select(Device).where(Device.user_id == user.id)))
    for device in devices:
        _delete_device_record(session, device)

    refresh_session_ids = list(
        session.scalars(select(AuthRefreshSession.id).where(AuthRefreshSession.user_id == user.id))
    )
    if refresh_session_ids:
        session.execute(
            update(AuthRefreshSession)
            .where(AuthRefreshSession.replaced_by_id.in_(refresh_session_ids))
            .values(replaced_by_id=None)
        )
    session.execute(delete(AuthHandoffCode).where(AuthHandoffCode.user_id == user.id))
    session.execute(delete(AuthRefreshSession).where(AuthRefreshSession.user_id == user.id))
    session.delete(user)
    session.commit()
