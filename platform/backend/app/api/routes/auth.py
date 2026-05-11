from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_session
from app.schemas.auth import AuthSessionRead, AuthUserRead, CurrentUserRead, DevLoginRequest
from app.services.dev_auth import issue_dev_token
from app.services.users import get_or_create_local_dev_user, get_user_by_id, upsert_google_user


router = APIRouter(tags=["auth"])
oauth = OAuth()


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


@router.get("/api/me")
def me(request: Request, session: Session = Depends(get_session)) -> CurrentUserRead:
    from app.api.deps import get_optional_current_user

    user = get_optional_current_user(request, session)
    if user is None:
        return CurrentUserRead(authenticated=False, user=None)

    return CurrentUserRead(
        authenticated=True,
        user=AuthUserRead(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
        ),
    )


@router.post("/api/auth/login", response_model=AuthSessionRead)
def dev_token_login(payload: DevLoginRequest, session: Session = Depends(get_session)) -> AuthSessionRead:
    settings = get_settings()
    if not settings.dev_token_auth_enabled:
        raise HTTPException(status_code=403, detail="Dev-only token auth is disabled.")

    user = get_or_create_local_dev_user(session, email=payload.email)
    token = issue_dev_token(settings, user.id)
    return AuthSessionRead(
        token=token,
        email=user.email,
        mode="api",
        user=AuthUserRead(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
        ),
    )
