from pydantic import BaseModel, Field


class DevLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class AuthUserRead(BaseModel):
    id: int
    email: str
    name: str | None
    avatar_url: str | None


class AuthSessionRead(BaseModel):
    token: str
    email: str
    mode: str
    user: AuthUserRead


class CurrentUserRead(BaseModel):
    authenticated: bool
    user: AuthUserRead | None
