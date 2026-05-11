import pytest

from app.core.settings import get_settings


def clear_settings_cache():
    get_settings.cache_clear()


def test_development_allows_default_session_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)
    monkeypatch.delenv("PLANTLAB_SESSION_SECRET", raising=False)
    clear_settings_cache()

    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.session_secret == "dev-only-change-me"
    clear_settings_cache()


def test_production_requires_secure_session_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://plantlab:secret@localhost:5432/plantlab")
    monkeypatch.setenv("PLANTLAB_PROVISIONING_SHARED_SECRET", "provision-secret")
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)
    monkeypatch.delenv("PLANTLAB_SESSION_SECRET", raising=False)
    clear_settings_cache()

    with pytest.raises(ValueError, match="APP_SECRET_KEY"):
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
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    clear_settings_cache()

    with pytest.raises(ValueError, match="GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET"):
        get_settings()

    clear_settings_cache()


def test_valid_production_settings(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://plantlab:secret@localhost:5432/plantlab")
    monkeypatch.setenv("APP_SECRET_KEY", "a-secure-production-session-secret")
    monkeypatch.setenv("PLANTLAB_PROVISIONING_SHARED_SECRET", "provision-secret")
    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "gcs")
    monkeypatch.setenv("GCS_BUCKET_NAME", "plantlab-images")
    clear_settings_cache()

    settings = get_settings()

    assert settings.is_production is True
    assert settings.database_url == "postgresql+psycopg://plantlab:secret@localhost:5432/plantlab"
    assert settings.session_secret == "a-secure-production-session-secret"
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
    monkeypatch.setenv("DB_HOST", "136.112.180.16")
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


def test_database_host_env_builds_direct_postgres_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PLANTLAB_DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUD_SQL_CONNECTION_NAME", raising=False)
    monkeypatch.setenv("DB_HOST", "136.112.180.16")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "plantlab")
    monkeypatch.setenv("DB_USER", "plantlab_user")
    monkeypatch.setenv("DB_PASSWORD", "secret password")
    clear_settings_cache()

    settings = get_settings()

    assert settings.database_url == (
        "postgresql+psycopg://plantlab_user:secret%20password@136.112.180.16:5433/plantlab"
    )
    clear_settings_cache()


def test_database_host_uses_default_database_identity(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PLANTLAB_DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUD_SQL_CONNECTION_NAME", raising=False)
    monkeypatch.setenv("DB_HOST", "136.112.180.16")
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.setenv("DB_PASSWORD", "secret password")
    clear_settings_cache()

    settings = get_settings()

    assert settings.database_url == (
        "postgresql+psycopg://plantlab_user:secret%20password@136.112.180.16:5432/plantlab"
    )
    clear_settings_cache()


def test_database_password_is_required_for_component_config(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PLANTLAB_DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUD_SQL_CONNECTION_NAME", raising=False)
    monkeypatch.setenv("DB_HOST", "136.112.180.16")
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    clear_settings_cache()

    with pytest.raises(ValueError, match="DB_PASSWORD"):
        get_settings()

    clear_settings_cache()


def test_production_cloud_run_env_builds_default_socket_database_url(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_SECRET_KEY", "a-secure-production-session-secret")
    monkeypatch.setenv("PLANTLAB_PROVISIONING_SHARED_SECRET", "provision-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PLANTLAB_DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUD_SQL_CONNECTION_NAME", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.setenv("DB_PASSWORD", "secret password")
    clear_settings_cache()

    settings = get_settings()

    assert settings.database_url == (
        "postgresql+psycopg://plantlab_user:secret%20password@/plantlab"
        "?host=/cloudsql/plantlab-493805:us-central1:plantlab"
    )

    clear_settings_cache()


def test_production_requires_database_password(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_SECRET_KEY", "a-secure-production-session-secret")
    monkeypatch.setenv("PLANTLAB_PROVISIONING_SHARED_SECRET", "provision-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PLANTLAB_DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    clear_settings_cache()

    with pytest.raises(ValueError, match="DB_PASSWORD"):
        get_settings()

    clear_settings_cache()


def test_production_startup_uses_migrations_not_create_all(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://plantlab:secret@localhost:5432/plantlab")
    monkeypatch.setenv("APP_SECRET_KEY", "a-secure-production-session-secret")
    monkeypatch.setenv("PLANTLAB_PROVISIONING_SHARED_SECRET", "provision-secret")
    clear_settings_cache()

    from app.db import session as db_session

    create_all_called = False

    def fake_create_all(_engine):
        nonlocal create_all_called
        create_all_called = True

    monkeypatch.setattr(db_session.Base.metadata, "create_all", fake_create_all)

    db_session.init_db()

    assert create_all_called is False
    clear_settings_cache()
