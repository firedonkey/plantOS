from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings
from app.models.base import Base
import app.models  # noqa: F401


def get_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(database_url: str | None = None) -> None:
    selected_engine = get_engine(database_url) if database_url else engine
    Base.metadata.create_all(selected_engine)
    _apply_lightweight_sqlite_migrations(selected_engine)


def _apply_lightweight_sqlite_migrations(selected_engine) -> None:
    if not selected_engine.url.drivername.startswith("sqlite"):
        return
    inspector = inspect(selected_engine)
    if "devices" not in inspector.get_table_names():
        return
    device_columns = {column["name"] for column in inspector.get_columns("devices")}
    with selected_engine.begin() as connection:
        if "api_token" not in device_columns:
            connection.execute(text("ALTER TABLE devices ADD COLUMN api_token VARCHAR(80)"))


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
