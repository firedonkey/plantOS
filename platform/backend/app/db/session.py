from collections.abc import Generator

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateColumn

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
    if database_url is None and get_settings().is_production:
        # Production schema changes should run through Alembic migrations.
        return
    Base.metadata.create_all(selected_engine)
    _apply_lightweight_migrations(selected_engine)


def _apply_lightweight_migrations(selected_engine) -> None:
    inspector = inspect(selected_engine)
    table_names = inspector.get_table_names()
    with selected_engine.begin() as connection:
        if "devices" in table_names:
            device_columns = {column["name"] for column in inspector.get_columns("devices")}
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("api_token", String(80)))
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("current_light_on", Boolean))
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("current_light_intensity_percent", Integer))
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("current_pump_on", Boolean))
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("status_message", String(160)))
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("status_updated_at", DateTime(timezone=True)))
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("released_at", DateTime(timezone=True)))
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("archived_at", DateTime(timezone=True)))
            _add_column_if_missing(connection, selected_engine, "devices", device_columns, Column("release_reason", String(80)))
        if "sensor_readings" in table_names:
            reading_columns = {column["name"] for column in inspector.get_columns("sensor_readings")}
            _add_column_if_missing(connection, selected_engine, "sensor_readings", reading_columns, Column("light_on", Boolean))
            _add_column_if_missing(connection, selected_engine, "sensor_readings", reading_columns, Column("light_intensity_percent", Integer))
            _add_column_if_missing(connection, selected_engine, "sensor_readings", reading_columns, Column("water_temperature_c", Float))
            _add_column_if_missing(connection, selected_engine, "sensor_readings", reading_columns, Column("water_level_raw", Integer))
            _add_column_if_missing(connection, selected_engine, "sensor_readings", reading_columns, Column("water_level_state", String(40)))
            _add_column_if_missing(connection, selected_engine, "sensor_readings", reading_columns, Column("pump_on", Boolean))
            _add_column_if_missing(connection, selected_engine, "sensor_readings", reading_columns, Column("pump_status", String(120)))
        if "images" in table_names:
            image_columns = {column["name"] for column in inspector.get_columns("images")}
            _add_column_if_missing(connection, selected_engine, "images", image_columns, Column("source_hardware_device_id", String(120)))
        if "commands" in table_names:
            command_columns = {column["name"] for column in inspector.get_columns("commands")}
            _add_column_if_missing(connection, selected_engine, "commands", command_columns, Column("light_on", Boolean))
            _add_column_if_missing(connection, selected_engine, "commands", command_columns, Column("light_intensity_percent", Integer))
            _add_column_if_missing(connection, selected_engine, "commands", command_columns, Column("pump_on", Boolean))
        if "device_hardware_ids" in table_names:
            node_columns = {column["name"] for column in inspector.get_columns("device_hardware_ids")}
            _add_column_if_missing(
                connection,
                selected_engine,
                "device_hardware_ids",
                node_columns,
                Column("node_role", String(40), nullable=False, server_default="single_board"),
            )
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("node_index", Integer))
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("display_name", String(120)))
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("hardware_model", String(120)))
            _add_column_if_missing(
                connection,
                selected_engine,
                "device_hardware_ids",
                node_columns,
                Column("status", String(40), nullable=False, server_default="provisioning"),
            )
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("software_version", String(120)))
            _add_column_if_missing(
                connection,
                selected_engine,
                "device_hardware_ids",
                node_columns,
                Column("ota_status", String(40), nullable=False, server_default="idle"),
            )
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("ota_available_version", String(120)))
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("ota_target_version", String(120)))
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("ota_release_id", String(80)))
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("ota_progress", Integer))
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("ota_error", String(240)))
            _add_column_if_missing(connection, selected_engine, "device_hardware_ids", node_columns, Column("ota_updated_at", DateTime(timezone=True)))
            _add_column_if_missing(
                connection,
                selected_engine,
                "device_hardware_ids",
                node_columns,
                Column("ota_last_success_at", DateTime(timezone=True)),
            )


def _add_column_if_missing(connection, selected_engine, table_name: str, existing_columns: set[str], column: Column) -> None:
    if column.name in existing_columns:
        return
    column_sql = str(CreateColumn(column).compile(dialect=selected_engine.dialect))
    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))
    existing_columns.add(column.name)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
