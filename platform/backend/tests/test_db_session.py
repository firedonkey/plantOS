from app.core.settings import get_settings
from app.db.session import get_engine


def clear_settings_cache():
    get_settings.cache_clear()


def test_postgres_engine_uses_pool_health_checks(monkeypatch):
    monkeypatch.setenv("PLANTLAB_DATABASE_POOL_PRE_PING", "true")
    monkeypatch.setenv("PLANTLAB_DATABASE_POOL_RECYCLE_SECONDS", "900")
    monkeypatch.setenv("PLANTLAB_DATABASE_POOL_SIZE", "2")
    monkeypatch.setenv("PLANTLAB_DATABASE_POOL_MAX_OVERFLOW", "1")
    monkeypatch.setenv("PLANTLAB_DATABASE_POOL_TIMEOUT_SECONDS", "5")
    clear_settings_cache()

    engine = get_engine("postgresql+psycopg://plantlab:secret@localhost:5432/plantlab")

    try:
        assert engine.pool._pre_ping is True
        assert engine.pool._recycle == 900
        assert engine.pool.size() == 2
        assert engine.pool._max_overflow == 1
        assert engine.pool._timeout == 5
    finally:
        engine.dispose()
        clear_settings_cache()


def test_pool_recycle_can_be_disabled(monkeypatch):
    monkeypatch.setenv("PLANTLAB_DATABASE_POOL_RECYCLE_SECONDS", "-1")
    clear_settings_cache()

    engine = get_engine("postgresql+psycopg://plantlab:secret@localhost:5432/plantlab")

    try:
        assert engine.pool._pre_ping is True
        assert engine.pool._recycle == -1
    finally:
        engine.dispose()
        clear_settings_cache()
