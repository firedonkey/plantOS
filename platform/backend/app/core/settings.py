import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv


PLATFORM_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = PLATFORM_DIR.parent
INFRA_ENV_DIR = ROOT_DIR / "infra" / "env"
DEFAULT_CLOUD_SQL_CONNECTION_NAME = "plantlab-493805:us-central1:plantlab"
DEFAULT_DB_NAME = "plantlab"
DEFAULT_DB_USER = "plantlab_user"

load_dotenv(ROOT_DIR / ".env")
load_dotenv(INFRA_ENV_DIR / ".env", override=True)
load_dotenv(INFRA_ENV_DIR / ".env.local", override=True)
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
    provisioning_api_url: str = "https://plantlab-provision-api-418533861080.us-central1.run.app"
    provisioning_public_url: str | None = None
    provisioning_service_secret: str | None = None
    local_setup_url: str = "http://10.42.0.1:8080/"
    device_platform_url: str | None = None
    dev_token_auth_enabled: bool = True
    standalone_web_origin_regex: str | None = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    standalone_access_token_ttl_seconds: int = 15 * 60
    standalone_refresh_token_ttl_days: int = 30
    standalone_refresh_cookie_name: str = "plantlab_refresh"
    standalone_refresh_cookie_samesite: str = "lax"
    standalone_refresh_cookie_secure: bool | None = None
    standalone_mobile_scheme: str | None = "plantlab"

    @property
    def google_auth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def effective_provisioning_public_url(self) -> str:
        return (self.provisioning_public_url or self.provisioning_api_url).rstrip("/")

    def validate(self) -> None:
        if self.is_production and self.database_url.startswith("sqlite"):
            raise ValueError("PostgreSQL DATABASE_URL or Cloud SQL DB_PASSWORD is required in production.")
        if self.storage_backend not in {"local", "gcs"}:
            raise ValueError("PLANTLAB_STORAGE_BACKEND must be 'local' or 'gcs'.")
        if self.storage_backend == "local" and not self.upload_dir:
            raise ValueError("PLANTLAB_UPLOAD_DIR is required when PLANTLAB_STORAGE_BACKEND=local.")
        if self.storage_backend == "gcs" and not self.gcs_bucket_name:
            raise ValueError("GCS_BUCKET_NAME is required when PLANTLAB_STORAGE_BACKEND=gcs.")
        if bool(self.google_client_id) != bool(self.google_client_secret):
            raise ValueError("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set together.")
        if self.is_production and not self.provisioning_service_secret:
            raise ValueError("PLANTLAB_PROVISIONING_SHARED_SECRET is required in production.")
        if self.is_production and self.session_secret == Settings.session_secret:
            raise ValueError("APP_SECRET_KEY must be set to a secure value in production.")
        if self.is_production and self.dev_token_auth_enabled:
            raise ValueError("PLANTLAB_DEV_TOKEN_AUTH_ENABLED cannot be enabled in production.")
        if self.standalone_access_token_ttl_seconds < 60:
            raise ValueError("PLANTLAB_STANDALONE_ACCESS_TOKEN_TTL_SECONDS must be at least 60.")
        if self.standalone_refresh_token_ttl_days < 1:
            raise ValueError("PLANTLAB_STANDALONE_REFRESH_TOKEN_TTL_DAYS must be at least 1.")
        if self.standalone_refresh_cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("PLANTLAB_STANDALONE_REFRESH_COOKIE_SAMESITE must be one of lax, strict, or none.")
        if self.standalone_refresh_cookie_samesite == "none" and self.effective_refresh_cookie_secure is False:
            raise ValueError("PLANTLAB_STANDALONE_REFRESH_COOKIE_SAMESITE=none requires a secure refresh cookie.")

    @property
    def effective_refresh_cookie_secure(self) -> bool:
        if self.standalone_refresh_cookie_secure is not None:
            return self.standalone_refresh_cookie_secure
        return self.is_production


@lru_cache
def get_settings() -> Settings:
    settings = Settings(
        app_env=os.getenv("APP_ENV", Settings.app_env).lower(),
        database_url=_database_url(),
        storage_backend=os.getenv("PLANTLAB_STORAGE_BACKEND", Settings.storage_backend).lower(),
        upload_dir=os.getenv("PLANTLAB_UPLOAD_DIR", Settings.upload_dir),
        gcs_bucket_name=_optional_env("GCS_BUCKET_NAME"),
        session_secret=_required_or_default_secret("APP_SECRET_KEY", legacy_name="PLANTLAB_SESSION_SECRET"),
        google_client_id=_optional_env("GOOGLE_OAUTH_CLIENT_ID", legacy_name="GOOGLE_CLIENT_ID"),
        google_client_secret=_optional_env("GOOGLE_OAUTH_CLIENT_SECRET", legacy_name="GOOGLE_CLIENT_SECRET"),
        provisioning_api_url=os.getenv("PLANTLAB_PROVISIONING_API_URL", Settings.provisioning_api_url).rstrip("/"),
        provisioning_public_url=_optional_env("PLANTLAB_PROVISIONING_PUBLIC_URL"),
        provisioning_service_secret=_optional_env("PLANTLAB_PROVISIONING_SHARED_SECRET"),
        local_setup_url=os.getenv("PLANTLAB_LOCAL_SETUP_URL", Settings.local_setup_url).rstrip("/") + "/",
        device_platform_url=_optional_env("PLANTLAB_DEVICE_PLATFORM_URL"),
        dev_token_auth_enabled=_env_bool(
            "PLANTLAB_DEV_TOKEN_AUTH_ENABLED",
            default=os.getenv("APP_ENV", Settings.app_env).lower() != "production",
        ),
        standalone_web_origin_regex=_optional_env(
            "PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX"
        )
        if os.getenv("PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX") is not None
        else (
            None
            if os.getenv("APP_ENV", Settings.app_env).lower() == "production"
            else Settings.standalone_web_origin_regex
        ),
        standalone_access_token_ttl_seconds=_env_int(
            "PLANTLAB_STANDALONE_ACCESS_TOKEN_TTL_SECONDS",
            default=Settings.standalone_access_token_ttl_seconds,
        ),
        standalone_refresh_token_ttl_days=_env_int(
            "PLANTLAB_STANDALONE_REFRESH_TOKEN_TTL_DAYS",
            default=Settings.standalone_refresh_token_ttl_days,
        ),
        standalone_refresh_cookie_name=os.getenv(
            "PLANTLAB_STANDALONE_REFRESH_COOKIE_NAME",
            Settings.standalone_refresh_cookie_name,
        ).strip()
        or Settings.standalone_refresh_cookie_name,
        standalone_refresh_cookie_samesite=os.getenv(
            "PLANTLAB_STANDALONE_REFRESH_COOKIE_SAMESITE",
            Settings.standalone_refresh_cookie_samesite,
        )
        .strip()
        .lower(),
        standalone_refresh_cookie_secure=_optional_env_bool("PLANTLAB_STANDALONE_REFRESH_COOKIE_SECURE"),
        standalone_mobile_scheme=(
            _optional_env("PLANTLAB_STANDALONE_MOBILE_SCHEME")
            if os.getenv("PLANTLAB_STANDALONE_MOBILE_SCHEME") is not None
            else Settings.standalone_mobile_scheme
        ),
    )
    settings.validate()
    return settings


def _optional_env(name: str, legacy_name: str | None = None) -> str | None:
    value = os.getenv(name)
    if (value is None or value.strip() == "") and legacy_name:
        value = os.getenv(legacy_name)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _optional_env_bool(name: str) -> bool | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _env_int(name: str, *, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _required_or_default_secret(name: str, legacy_name: str | None = None) -> str:
    return _optional_env(name, legacy_name=legacy_name) or Settings.session_secret


def _database_url() -> str:
    explicit_url = _optional_env("PLANTLAB_DATABASE_URL") or _optional_env("DATABASE_URL")
    if explicit_url:
        return _normalize_database_url(explicit_url)

    is_production = os.getenv("APP_ENV", Settings.app_env).lower() == "production"
    cloud_sql_connection_name = _optional_env("CLOUD_SQL_CONNECTION_NAME")
    if is_production and not cloud_sql_connection_name:
        cloud_sql_connection_name = DEFAULT_CLOUD_SQL_CONNECTION_NAME

    db_host = _optional_env("DB_HOST")
    db_port = _optional_env("DB_PORT") or "5432"
    db_name = _optional_env("DB_NAME") or DEFAULT_DB_NAME
    db_user = _optional_env("DB_USER") or DEFAULT_DB_USER
    db_password = _optional_env("DB_PASSWORD")
    db_parts = {
        "DB_PASSWORD": db_password,
    }

    if cloud_sql_connection_name:
        _require_database_parts(db_parts, extra_message="Cloud SQL requires DB_PASSWORD.")
        return _cloud_sql_postgres_url(
            connection_name=cloud_sql_connection_name,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
        )

    if db_host:
        _require_database_parts(db_parts, extra_message="DB_HOST requires DB_PASSWORD.")
        return _host_postgres_url(
            host=db_host,
            port=db_port,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
        )

    return Settings.database_url


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def _cloud_sql_postgres_url(
    *,
    connection_name: str,
    db_name: str,
    db_user: str,
    db_password: str,
) -> str:
    user = quote(db_user)
    password = quote(db_password)
    database = quote(db_name)
    socket_path = quote(f"/cloudsql/{connection_name}", safe="/:")
    return f"postgresql+psycopg://{user}:{password}@/{database}?host={socket_path}"


def _host_postgres_url(
    *,
    host: str,
    port: str,
    db_name: str,
    db_user: str,
    db_password: str,
) -> str:
    user = quote(db_user)
    password = quote(db_password)
    database = quote(db_name)
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


def _require_database_parts(db_parts: dict[str, str | None], extra_message: str | None = None) -> None:
    missing = [name for name, value in db_parts.items() if not value]
    if missing:
        message = f"Missing database environment variable(s): {', '.join(missing)}."
        if extra_message:
            message = f"{message} {extra_message}"
        raise ValueError(message)
