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
    monkeypatch.setenv("PLANTLAB_SESSION_SECRET", "a-secure-production-session-secret")
    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "gcs")
    monkeypatch.setenv("GCS_BUCKET_NAME", "plantlab-images")
    clear_settings_cache()

    settings = get_settings()

    assert settings.is_production is True
    assert settings.storage_backend == "gcs"
    assert settings.gcs_bucket_name == "plantlab-images"
    clear_settings_cache()
