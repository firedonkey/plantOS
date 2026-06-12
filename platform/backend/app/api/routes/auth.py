import json
import re
import secrets
from urllib.parse import urlencode, urlparse

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.settings import get_settings
from app.db.session import get_session
from app.models import User
from app.schemas.auth import (
    AppleMobileLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRead,
    AuthRefreshRequest,
    AuthSessionRead,
    AuthUserRead,
    CurrentUserRead,
    DevLoginRequest,
)
from app.services.apple_auth import verify_apple_identity_token
from app.services.dev_auth import issue_dev_token
from app.services.standalone_auth import (
    consume_handoff_code,
    create_handoff_code,
    create_refresh_session,
    issue_access_token,
    revoke_refresh_token,
    rotate_refresh_session,
)
from app.services.demo import demo_forbidden_message, is_demo_user
from app.services.users import (
    delete_user_account,
    get_or_create_demo_user,
    get_or_create_local_dev_user,
    get_user_by_id,
    upsert_apple_user,
    upsert_google_user,
)


router = APIRouter(tags=["auth"])
oauth = OAuth()
STANDALONE_AUTH_SESSION_KEY = "standalone_auth"
STANDALONE_APPLE_AUTH_SESSION_KEY = "standalone_apple_auth"
APPLE_AUTHORIZATION_URL = "https://appleid.apple.com/auth/authorize"


def _register_google_client() -> None:
    settings = get_settings()
    if not settings.google_auth_configured or "google" in oauth._clients:
        return

    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _auth_user_read(user: User) -> AuthUserRead:
    settings = get_settings()
    return AuthUserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_admin=(user.email or "").strip().lower() in settings.effective_admin_emails,
        is_demo_user=bool(getattr(user, "is_demo_user", False)),
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.standalone_refresh_cookie_name,
        refresh_token,
        max_age=settings.standalone_refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.effective_refresh_cookie_secure,
        samesite=settings.standalone_refresh_cookie_samesite,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.standalone_refresh_cookie_name,
        secure=settings.effective_refresh_cookie_secure,
        samesite=settings.standalone_refresh_cookie_samesite,
        path="/api/auth",
    )


def _validated_return_to(request: Request, client: str, return_to: str | None) -> str:
    candidate = (return_to or "").strip()
    if not candidate:
        return "/" if client == "web" else _mobile_callback_url(error="missing_return_to")

    parsed = urlparse(candidate)
    if parsed.scheme == "" and parsed.netloc == "" and candidate.startswith("/"):
        return candidate

    settings = get_settings()
    if client == "web":
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
        if settings.standalone_web_origin_regex and origin and re.fullmatch(
            settings.standalone_web_origin_regex,
            origin,
        ):
            return candidate

    if client == "mobile" and settings.standalone_mobile_scheme and parsed.scheme == settings.standalone_mobile_scheme:
        return candidate

    raise api_error(400, "invalid_return_to", "The auth return_to URL is not allowed.")


def _mobile_callback_url(*, handoff_code: str | None = None, error: str | None = None) -> str:
    settings = get_settings()
    scheme = settings.standalone_mobile_scheme or "plantlab"
    query = urlencode({key: value for key, value in {"handoff_code": handoff_code, "error": error}.items() if value})
    return f"{scheme}://auth/callback" + (f"?{query}" if query else "")


def _redirect_with_query(url: str, **params: str) -> RedirectResponse:
    separator = "&" if "?" in url else "?"
    return RedirectResponse(url=f"{url}{separator}{urlencode(params)}", status_code=303)


def _apple_authorize_url(*, client_id: str, redirect_uri: str, state: str, nonce: str) -> str:
    params = {
        "response_type": "code id_token",
        "response_mode": "form_post",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "name email",
        "state": state,
        "nonce": nonce,
    }
    return f"{APPLE_AUTHORIZATION_URL}?{urlencode(params)}"


def _apple_display_name(raw_user: str | None) -> str | None:
    if not raw_user:
        return None
    try:
        payload = json.loads(raw_user)
    except (TypeError, ValueError):
        return None
    name = payload.get("name") if isinstance(payload, dict) else None
    if not isinstance(name, dict):
        return None
    parts = [
        str(name.get("firstName") or "").strip(),
        str(name.get("lastName") or "").strip(),
    ]
    return " ".join(part for part in parts if part) or None


def _refresh_read(
    *,
    user: User,
    access_token: str,
    expires_in: int,
    expires_at: str,
    refresh_token: str | None = None,
) -> AuthRefreshRead:
    return AuthRefreshRead(
        access_token=access_token,
        expires_in=expires_in,
        expires_at=expires_at,
        refresh_token=refresh_token,
        user=_auth_user_read(user),
    )


@router.get("/auth/login")
async def login(request: Request):
    settings = get_settings()
    if not settings.google_auth_configured:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET.",
        )

    _register_google_client()
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request, session: Session = Depends(get_session)):
    _register_google_client()
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if not user_info:
        user_info = await oauth.google.userinfo(token=token)

    email = user_info.get("email")
    google_sub = user_info.get("sub")
    if not email or not google_sub:
        raise HTTPException(status_code=400, detail="Google account did not return email and subject.")

    user = upsert_google_user(
        session,
        google_sub=google_sub,
        email=email,
        name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
    )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get("/api/auth/google/start")
async def standalone_google_start(request: Request, client: str = "web", return_to: str | None = None):
    settings = get_settings()
    if not settings.google_auth_configured:
        raise api_error(
            503,
            "google_auth_not_configured",
            "Google sign-in is not configured for standalone auth.",
        )

    normalized_client = client.strip().lower()
    if normalized_client not in {"web", "mobile"}:
        raise api_error(400, "invalid_auth_client", "Auth client must be web or mobile.")

    redirect_target = _validated_return_to(request, normalized_client, return_to)
    request.session[STANDALONE_AUTH_SESSION_KEY] = {
        "client": normalized_client,
        "return_to": redirect_target,
    }
    _register_google_client()
    redirect_uri = request.url_for("standalone_auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/api/auth/google/callback", name="standalone_auth_callback")
async def standalone_google_callback(request: Request, session: Session = Depends(get_session)):
    _register_google_client()
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if not user_info:
        user_info = await oauth.google.userinfo(token=token)

    email = user_info.get("email")
    google_sub = user_info.get("sub")
    if not email or not google_sub:
        raise api_error(400, "google_identity_incomplete", "Google account did not return email and subject.")

    user = upsert_google_user(
        session,
        google_sub=google_sub,
        email=email,
        name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
    )
    request.session["user_id"] = user.id

    auth_state = request.session.pop(STANDALONE_AUTH_SESSION_KEY, {}) or {}
    client = auth_state.get("client") if auth_state.get("client") in {"web", "mobile"} else "web"
    return_to = auth_state.get("return_to") or ("/" if client == "web" else _mobile_callback_url())

    if client == "mobile":
        handoff_code = create_handoff_code(session, user.id)
        return _redirect_with_query(return_to, handoff_code=handoff_code)

    refresh_bundle = create_refresh_session(get_settings(), session, user.id)
    response = _redirect_with_query(return_to, auth="complete")
    _set_refresh_cookie(response, refresh_bundle.token)
    return response


@router.get("/api/auth/apple/start")
async def standalone_apple_start(request: Request, client: str = "web", return_to: str | None = None):
    settings = get_settings()
    if not settings.apple_web_auth_configured:
        raise api_error(
            503,
            "apple_auth_not_configured",
            "Apple sign-in is not configured for standalone web auth.",
        )

    normalized_client = client.strip().lower()
    if normalized_client != "web":
        raise api_error(400, "invalid_auth_client", "Apple web auth only supports the web client.")

    redirect_target = _validated_return_to(request, normalized_client, return_to)
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    request.session[STANDALONE_APPLE_AUTH_SESSION_KEY] = {
        "client": normalized_client,
        "return_to": redirect_target,
        "state": state,
        "nonce": nonce,
    }
    redirect_uri = str(request.url_for("standalone_apple_callback"))
    return RedirectResponse(
        url=_apple_authorize_url(
            client_id=settings.apple_web_client_id or "",
            redirect_uri=redirect_uri,
            state=state,
            nonce=nonce,
        ),
        status_code=303,
    )


@router.post("/api/auth/apple/callback", name="standalone_apple_callback")
async def standalone_apple_callback(request: Request, session: Session = Depends(get_session)):
    settings = get_settings()
    auth_state = request.session.pop(STANDALONE_APPLE_AUTH_SESSION_KEY, {}) or {}
    return_to = auth_state.get("return_to") or "/login"

    form = await request.form()
    if form.get("error"):
        raise api_error(401, "apple_auth_failed", "Apple sign-in was cancelled or failed.")

    expected_state = str(auth_state.get("state") or "")
    returned_state = str(form.get("state") or "")
    if not expected_state or not returned_state or not secrets.compare_digest(expected_state, returned_state):
        raise api_error(400, "invalid_apple_state", "Apple sign-in state did not match.")

    identity_token = str(form.get("id_token") or "")
    if not identity_token:
        raise api_error(400, "apple_identity_missing", "Apple sign-in did not return an identity token.")

    try:
        identity = verify_apple_identity_token(
            identity_token,
            audience=settings.apple_web_client_id or "",
            nonce=str(auth_state.get("nonce") or ""),
        )
    except Exception:
        raise api_error(401, "invalid_apple_identity", "Apple sign-in did not return a valid identity token.")

    user = upsert_apple_user(
        session,
        apple_sub=identity.sub,
        email=identity.email,
        name=_apple_display_name(str(form.get("user") or "") or None),
    )
    request.session["user_id"] = user.id

    refresh_bundle = create_refresh_session(settings, session, user.id)
    response = _redirect_with_query(return_to, auth="complete")
    _set_refresh_cookie(response, refresh_bundle.token)
    return response


@router.post("/api/auth/refresh", response_model=AuthRefreshRead)
def refresh(
    request: Request,
    response: Response,
    payload: AuthRefreshRequest | None = None,
    session: Session = Depends(get_session),
) -> AuthRefreshRead:
    settings = get_settings()
    body = payload or AuthRefreshRequest()
    cookie_token = request.cookies.get(settings.standalone_refresh_cookie_name)
    raw_refresh_token = cookie_token or body.refresh_token

    refresh_token_for_response: str | None = None
    if body.handoff_code:
        refresh_bundle = consume_handoff_code(settings, session, body.handoff_code)
        refresh_token_for_response = refresh_bundle.token if refresh_bundle is not None else None
    elif raw_refresh_token:
        refresh_bundle = rotate_refresh_session(settings, session, raw_refresh_token)
        if body.refresh_token:
            refresh_token_for_response = refresh_bundle.token if refresh_bundle is not None else None
    else:
        refresh_bundle = None

    if refresh_bundle is None:
        _clear_refresh_cookie(response)
        raise api_error(401, "invalid_refresh", "Refresh session is missing, expired, or revoked.")

    user = get_user_by_id(session, refresh_bundle.session.user_id)
    if user is None:
        revoke_refresh_token(session, refresh_bundle.token)
        _clear_refresh_cookie(response)
        raise api_error(401, "invalid_refresh", "Refresh session is missing, expired, or revoked.")

    if cookie_token:
        _set_refresh_cookie(response, refresh_bundle.token)

    access = issue_access_token(settings, user.id)
    return _refresh_read(
        user=user,
        access_token=access.token,
        expires_in=access.expires_in,
        expires_at=access.expires_at.isoformat(),
        refresh_token=refresh_token_for_response,
    )


@router.post("/api/auth/logout")
def standalone_logout(
    request: Request,
    response: Response,
    payload: AuthLogoutRequest | None = None,
    session: Session = Depends(get_session),
):
    settings = get_settings()
    body = payload or AuthLogoutRequest()
    revoke_refresh_token(session, request.cookies.get(settings.standalone_refresh_cookie_name))
    revoke_refresh_token(session, body.refresh_token)
    _clear_refresh_cookie(response)
    return {"ok": True}


@router.post("/api/auth/apple/mobile", response_model=AuthRefreshRead)
def standalone_apple_mobile_login(
    payload: AppleMobileLoginRequest,
    session: Session = Depends(get_session),
) -> AuthRefreshRead:
    settings = get_settings()
    try:
        identity = verify_apple_identity_token(payload.identity_token, audience=settings.apple_client_id)
    except Exception:
        raise api_error(401, "invalid_apple_identity", "Apple sign-in did not return a valid identity token.")

    email = (identity.email or payload.email or "").strip().lower() or None
    user = upsert_apple_user(
        session,
        apple_sub=identity.sub,
        email=email,
        name=(payload.full_name or "").strip() or None,
    )

    refresh_bundle = create_refresh_session(settings, session, user.id)
    access = issue_access_token(settings, user.id)
    return _refresh_read(
        user=user,
        access_token=access.token,
        expires_in=access.expires_in,
        expires_at=access.expires_at.isoformat(),
        refresh_token=refresh_bundle.token,
    )


@router.post("/api/auth/demo", response_model=AuthRefreshRead)
def demo_login(
    response: Response,
    session: Session = Depends(get_session),
) -> AuthRefreshRead:
    settings = get_settings()
    user = get_or_create_demo_user(session)
    refresh_bundle = create_refresh_session(settings, session, user.id)
    access = issue_access_token(settings, user.id)
    _set_refresh_cookie(response, refresh_bundle.token)
    return _refresh_read(
        user=user,
        access_token=access.token,
        expires_in=access.expires_in,
        expires_at=access.expires_at.isoformat(),
        refresh_token=refresh_bundle.token,
    )


@router.get("/api/me")
def me(request: Request, session: Session = Depends(get_session)) -> CurrentUserRead:
    from app.api.deps import get_optional_current_user

    user = get_optional_current_user(request, session)
    if user is None:
        return CurrentUserRead(authenticated=False, user=None)

    return CurrentUserRead(
        authenticated=True,
        user=_auth_user_read(user),
    )


@router.delete("/api/me")
def delete_me(request: Request, response: Response, session: Session = Depends(get_session)):
    from app.api.deps import get_current_user

    user = get_current_user(request, session)
    if is_demo_user(user):
        raise api_error(403, "demo_account_read_only", demo_forbidden_message("delete"))
    delete_user_account(session, user)
    _clear_refresh_cookie(response)
    return {"ok": True}


@router.post("/api/auth/login", response_model=AuthSessionRead)
def dev_token_login(payload: DevLoginRequest, session: Session = Depends(get_session)) -> AuthSessionRead:
    settings = get_settings()
    if not settings.dev_token_auth_enabled:
        raise api_error(
            403,
            "dev_token_auth_disabled",
            "Dev-only token auth is disabled.",
        )

    user = get_or_create_local_dev_user(session, email=payload.email)
    token = issue_dev_token(settings, user.id)
    return AuthSessionRead(
        token=token,
        email=user.email,
        mode="api",
        user=_auth_user_read(user),
    )
