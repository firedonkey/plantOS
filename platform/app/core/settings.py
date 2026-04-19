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


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("PLANTLAB_DATABASE_URL", Settings.database_url),
        storage_backend=os.getenv("PLANTLAB_STORAGE_BACKEND", Settings.storage_backend).lower(),
        upload_dir=os.getenv("PLANTLAB_UPLOAD_DIR", Settings.upload_dir),
        gcs_bucket_name=os.getenv("GCS_BUCKET_NAME"),
        session_secret=os.getenv("PLANTLAB_SESSION_SECRET", Settings.session_secret),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )
