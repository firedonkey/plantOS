from hashlib import sha256

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import AuthHandoffCode, AuthRefreshSession, Device, User
from app.services.devices import _delete_device_record


def _provider_fallback_email(provider: str, provider_sub: str) -> str:
    digest = sha256(provider_sub.encode("utf-8")).hexdigest()[:16]
    return f"{provider}-{digest}@auth.plantlab.local"


def _email_owner(session: Session, email: str | None) -> User | None:
    if not email:
        return None
    return session.scalar(select(User).where(User.email == email.strip().lower()))


def _revoke_user_auth_artifacts(session: Session, user_id: int) -> None:
    refresh_session_ids = list(
        session.scalars(select(AuthRefreshSession.id).where(AuthRefreshSession.user_id == user_id))
    )
    if refresh_session_ids:
        session.execute(
            update(AuthRefreshSession)
            .where(AuthRefreshSession.replaced_by_id.in_(refresh_session_ids))
            .values(replaced_by_id=None)
        )
    session.execute(delete(AuthHandoffCode).where(AuthHandoffCode.user_id == user_id))
    session.execute(delete(AuthRefreshSession).where(AuthRefreshSession.user_id == user_id))


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
    normalized_email = email.strip().lower()
    user = session.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        email_user = _email_owner(session, normalized_email)
        if (
            email_user is not None
            and (email_user.google_sub in (None, google_sub))
            and email_user.apple_sub is None
        ):
            user = email_user

    if user is None:
        account_email = (
            normalized_email
            if _email_owner(session, normalized_email) is None
            else _provider_fallback_email("google", google_sub)
        )
        user = User(email=account_email, google_sub=google_sub)
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
) -> User:
    normalized_email = email.strip().lower() if email else None
    user = session.scalar(select(User).where(User.apple_sub == apple_sub))
    if user is not None and user.google_sub:
        # There is no explicit account-linking flow yet. If a previous release
        # linked Apple to a Google-owned row by matching email, split the Apple
        # identity into its own account on the next Apple sign-in.
        if user.id is not None:
            _revoke_user_auth_artifacts(session, user.id)
        user.apple_sub = None
        session.flush()
        user = None

    if user is None:
        email_user = _email_owner(session, normalized_email)
        account_email = (
            normalized_email
            if normalized_email and email_user is None
            else _provider_fallback_email("apple", apple_sub)
        )
        user = User(email=account_email, apple_sub=apple_sub)
        session.add(user)
    elif normalized_email and user.email.startswith("apple-") and user.email.endswith("@auth.plantlab.local"):
        email_user = _email_owner(session, normalized_email)
        if email_user is None:
            user.email = normalized_email

    if name:
        user.name = name
    elif not user.name:
        user.name = "Apple User"
    user.apple_sub = apple_sub
    session.commit()
    session.refresh(user)
    return user


def delete_user_account(session: Session, user: User) -> None:
    devices = list(session.scalars(select(Device).where(Device.user_id == user.id)))
    for device in devices:
        _delete_device_record(session, device)

    _revoke_user_auth_artifacts(session, user.id)
    session.delete(user)
    session.commit()
