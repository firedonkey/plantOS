from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.models import AuthHandoffCode, AuthRefreshSession, User
from app.services.users import get_user_by_id


ACCESS_TOKEN_SALT = "plantlab-standalone-access-token"
REFRESH_TOKEN_BYTES = 32
HANDOFF_CODE_BYTES = 32
HANDOFF_CODE_TTL_SECONDS = 5 * 60


@dataclass(frozen=True)
class AccessTokenBundle:
    token: str
    expires_at: datetime
    expires_in: int


@dataclass(frozen=True)
class RefreshSessionBundle:
    token: str
    session: AuthRefreshSession


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def issue_access_token(settings: Settings, user_id: int) -> AccessTokenBundle:
    issued_at = utcnow()
    expires_at = issued_at + timedelta(seconds=settings.standalone_access_token_ttl_seconds)
    serializer = URLSafeTimedSerializer(settings.session_secret, salt=ACCESS_TOKEN_SALT)
    token = serializer.dumps(
        {
            "user_id": user_id,
            "mode": "standalone",
            "iat": int(issued_at.timestamp()),
        }
    )
    return AccessTokenBundle(
        token=token,
        expires_at=expires_at,
        expires_in=settings.standalone_access_token_ttl_seconds,
    )


def read_access_token(settings: Settings, token: str) -> int | None:
    serializer = URLSafeTimedSerializer(settings.session_secret, salt=ACCESS_TOKEN_SALT)
    try:
        payload = serializer.loads(token, max_age=settings.standalone_access_token_ttl_seconds)
    except (BadSignature, SignatureExpired):
        return None

    if payload.get("mode") != "standalone":
        return None

    user_id = payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        return None
    return user_id


def get_user_from_access_token(settings: Settings, session: Session, token: str) -> User | None:
    user_id = read_access_token(settings, token)
    if user_id is None:
        return None
    return get_user_by_id(session, user_id)


def create_refresh_session(settings: Settings, session: Session, user_id: int) -> RefreshSessionBundle:
    raw_token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    refresh_session = AuthRefreshSession(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=utcnow() + timedelta(days=settings.standalone_refresh_token_ttl_days),
    )
    session.add(refresh_session)
    session.commit()
    session.refresh(refresh_session)
    return RefreshSessionBundle(token=raw_token, session=refresh_session)


def rotate_refresh_session(
    settings: Settings,
    session: Session,
    raw_token: str,
) -> RefreshSessionBundle | None:
    refresh_session = get_active_refresh_session(session, raw_token)
    if refresh_session is None:
        return None

    now = utcnow()
    refresh_session.last_used_at = now
    refresh_session.revoked_at = now
    raw_next_token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    next_session = AuthRefreshSession(
        user_id=refresh_session.user_id,
        token_hash=hash_token(raw_next_token),
        expires_at=now + timedelta(days=settings.standalone_refresh_token_ttl_days),
    )
    session.add(next_session)
    session.flush()
    refresh_session.replaced_by_id = next_session.id
    session.commit()
    session.refresh(next_session)
    return RefreshSessionBundle(token=raw_next_token, session=next_session)


def revoke_refresh_token(session: Session, raw_token: str | None) -> bool:
    if not raw_token:
        return False

    refresh_session = session.scalar(
        select(AuthRefreshSession).where(AuthRefreshSession.token_hash == hash_token(raw_token))
    )
    if refresh_session is None:
        return False

    if refresh_session.revoked_at is None:
        refresh_session.revoked_at = utcnow()
        session.commit()
    return True


def get_active_refresh_session(session: Session, raw_token: str) -> AuthRefreshSession | None:
    refresh_session = session.scalar(
        select(AuthRefreshSession).where(AuthRefreshSession.token_hash == hash_token(raw_token))
    )
    if refresh_session is None:
        return None
    if refresh_session.revoked_at is not None:
        return None
    if as_aware_utc(refresh_session.expires_at) <= utcnow():
        return None
    return refresh_session


def create_handoff_code(session: Session, user_id: int) -> str:
    raw_code = secrets.token_urlsafe(HANDOFF_CODE_BYTES)
    handoff = AuthHandoffCode(
        user_id=user_id,
        code_hash=hash_token(raw_code),
        expires_at=utcnow() + timedelta(seconds=HANDOFF_CODE_TTL_SECONDS),
    )
    session.add(handoff)
    session.commit()
    return raw_code


def consume_handoff_code(settings: Settings, session: Session, raw_code: str) -> RefreshSessionBundle | None:
    handoff = session.scalar(select(AuthHandoffCode).where(AuthHandoffCode.code_hash == hash_token(raw_code)))
    if handoff is None:
        return None
    if handoff.consumed_at is not None:
        return None
    if as_aware_utc(handoff.expires_at) <= utcnow():
        return None

    handoff.consumed_at = utcnow()
    bundle = create_refresh_session(settings, session, handoff.user_id)
    return bundle


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
