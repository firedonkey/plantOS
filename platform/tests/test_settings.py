import pytest

from app.core.settings import get_settings


def clear_settings_cache():
    get_settings.cache_clear()


def test_development_allows_default_session_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("PLANTLAB_SESSION_SECRET", raising=False)
    clear_settings_cache()

    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.session_secret == "dev-only-change-me"
    clear_settings_cache()


def test_production_requires_secure_session_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://plantlab:secret@localhost:5432/plantlab")
    monkeypatch.delenv("PLANTLAB_SESSION_SECRET", raising=False)
    clear_settings_cache()

    with pytest.raises(ValueError, match="PLANTLAB_SESSION_SECRET"):
        get_settings()

    clear_settings_cache()


def test_gcs_storage_requires_bucket(monkeypatch):
    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "gcs")
    monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
    clear_settings_cache()

    with pytest.raises(ValueError, match="GCS_BUCKET_NAME"):
        get_settings()

    clear_settings_cache()


def test_google_oauth_env_vars_must_be_set_together(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    clear_settings_cache()

    with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"):
        get_settings()

    clear_settings_cache()


def test_valid_production_settings(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://plantlab:secret@localhost:5432/plantlab")
    monkeypatch.setenv("PLANTLAB_SESSION_SECRET", "a-secure-production-session-secret")
    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "gcs")
    monkeypatch.setenv("GCS_BUCKET_NAME", "plantlab-images")
    clear_settings_cache()

    settings = get_settings()

    assert settings.is_production is True
    assert settings.database_url == "postgresql+psycopg://plantlab:secret@localhost:5432/plantlab"
    assert settings.storage_backend == "gcs"
    assert settings.gcs_bucket_name == "plantlab-images"
    clear_settings_cache()


def test_standard_database_url_is_supported(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://plantlab:secret@localhost:5432/plantlab")
    monkeypatch.delenv("PLANTLAB_DATABASE_URL", raising=False)
    clear_settings_cache()

    settings = get_settings()

    assert settings.database_url == "postgresql+psycopg://plantlab:secret@localhost:5432/plantlab"
    clear_settings_cache()


def test_plantlab_database_url_takes_precedence(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://ignored:secret@localhost:5432/ignored")
    monkeypatch.setenv("PLANTLAB_DATABASE_URL", "sqlite:///./custom.db")
    clear_settings_cache()

    settings = get_settings()

    assert settings.database_url == "sqlite:///./custom.db"
    clear_settings_cache()


def test_cloud_sql_env_builds_socket_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PLANTLAB_DATABASE_URL", raising=False)
    monkeypatch.setenv("CLOUD_SQL_CONNECTION_NAME", "plantlab-project:us-west1:plantlab-postgres")
    monkeypatch.setenv("DB_NAME", "plantlab")
    monkeypatch.setenv("DB_USER", "plantlab_user")
    monkeypatch.setenv("DB_PASSWORD", "secret password")
    clear_settings_cache()

    settings = get_settings()

    assert settings.database_url == (
        "postgresql+psycopg://plantlab_user:secret%20password@/plantlab"
        "?host=/cloudsql/plantlab-project:us-west1:plantlab-postgres"
    )
    clear_settings_cache()


def test_production_rejects_sqlite_database(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PLANTLAB_SESSION_SECRET", "a-secure-production-session-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PLANTLAB_DATABASE_URL", raising=False)
    clear_settings_cache()

    with pytest.raises(ValueError, match="PostgreSQL"):
        get_settings()

    clear_settings_cache()
