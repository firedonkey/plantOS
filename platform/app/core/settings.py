import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PLATFORM_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = PLATFORM_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(PLATFORM_DIR / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    app_name: str = "PlantLab Platform"
    version: str = "0.1.0"
    app_env: str = "development"
    database_url: str = "sqlite:///./data/platform.db"
    storage_backend: str = "local"
    upload_dir: str = "data/uploads"
    gcs_bucket_name: str | None = None
    session_secret: str = "dev-only-change-me"
    google_client_id: str | None = None
    google_client_secret: str | None = None

    @property
    def google_auth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate(self) -> None:
        if self.storage_backend not in {"local", "gcs"}:
            raise ValueError("PLANTLAB_STORAGE_BACKEND must be 'local' or 'gcs'.")
        if self.storage_backend == "local" and not self.upload_dir:
            raise ValueError("PLANTLAB_UPLOAD_DIR is required when PLANTLAB_STORAGE_BACKEND=local.")
        if self.storage_backend == "gcs" and not self.gcs_bucket_name:
            raise ValueError("GCS_BUCKET_NAME is required when PLANTLAB_STORAGE_BACKEND=gcs.")
        if bool(self.google_client_id) != bool(self.google_client_secret):
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set together.")
        if self.is_production and self.session_secret == Settings.session_secret:
            raise ValueError("PLANTLAB_SESSION_SECRET must be set to a secure value in production.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings(
        app_env=os.getenv("APP_ENV", Settings.app_env).lower(),
        database_url=os.getenv("PLANTLAB_DATABASE_URL", Settings.database_url),
        storage_backend=os.getenv("PLANTLAB_STORAGE_BACKEND", Settings.storage_backend).lower(),
        upload_dir=os.getenv("PLANTLAB_UPLOAD_DIR", Settings.upload_dir),
        gcs_bucket_name=_optional_env("GCS_BUCKET_NAME"),
        session_secret=os.getenv("PLANTLAB_SESSION_SECRET", Settings.session_secret),
        google_client_id=_optional_env("GOOGLE_CLIENT_ID"),
        google_client_secret=_optional_env("GOOGLE_CLIENT_SECRET"),
    )
    settings.validate()
    return settings


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value
