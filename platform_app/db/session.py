from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from platform_app.core.settings import get_settings
from platform_app.models.base import Base
import platform_app.models  # noqa: F401


def get_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(database_url: str | None = None) -> None:
    selected_engine = get_engine(database_url) if database_url else engine
    Base.metadata.create_all(selected_engine)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
