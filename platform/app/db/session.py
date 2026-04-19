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
    table_names = inspector.get_table_names()
    with selected_engine.begin() as connection:
        if "devices" in table_names:
            device_columns = {column["name"] for column in inspector.get_columns("devices")}
            if "api_token" not in device_columns:
                connection.execute(text("ALTER TABLE devices ADD COLUMN api_token VARCHAR(80)"))
            if "current_light_on" not in device_columns:
                connection.execute(text("ALTER TABLE devices ADD COLUMN current_light_on BOOLEAN"))
            if "current_pump_on" not in device_columns:
                connection.execute(text("ALTER TABLE devices ADD COLUMN current_pump_on BOOLEAN"))
            if "status_message" not in device_columns:
                connection.execute(text("ALTER TABLE devices ADD COLUMN status_message VARCHAR(160)"))
            if "status_updated_at" not in device_columns:
                connection.execute(text("ALTER TABLE devices ADD COLUMN status_updated_at DATETIME"))
        if "sensor_readings" in table_names:
            reading_columns = {column["name"] for column in inspector.get_columns("sensor_readings")}
            if "light_on" not in reading_columns:
                connection.execute(text("ALTER TABLE sensor_readings ADD COLUMN light_on BOOLEAN"))
            if "pump_on" not in reading_columns:
                connection.execute(text("ALTER TABLE sensor_readings ADD COLUMN pump_on BOOLEAN"))
            if "pump_status" not in reading_columns:
                connection.execute(text("ALTER TABLE sensor_readings ADD COLUMN pump_status VARCHAR(120)"))
        if "commands" in table_names:
            command_columns = {column["name"] for column in inspector.get_columns("commands")}
            if "light_on" not in command_columns:
                connection.execute(text("ALTER TABLE commands ADD COLUMN light_on BOOLEAN"))
            if "pump_on" not in command_columns:
                connection.execute(text("ALTER TABLE commands ADD COLUMN pump_on BOOLEAN"))


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
