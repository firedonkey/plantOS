from pydantic import BaseModel, Field


class DevLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class AuthUserRead(BaseModel):
    id: int
    email: str
    name: str | None
    avatar_url: str | None
    is_admin: bool = False
    is_demo_user: bool = False


class AuthSessionRead(BaseModel):
    token: str
    email: str
    mode: str
    user: AuthUserRead


class AuthRefreshRequest(BaseModel):
    refresh_token: str | None = None
    handoff_code: str | None = None


class AuthLogoutRequest(BaseModel):
    refresh_token: str | None = None


class AppleMobileLoginRequest(BaseModel):
    identity_token: str = Field(min_length=20)
    email: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)


class AuthRefreshRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: str
    mode: str = "standalone"
    user: AuthUserRead
    refresh_token: str | None = None


class CurrentUserRead(BaseModel):
    authenticated: bool
    user: AuthUserRead | None
