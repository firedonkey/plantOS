from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.db.session import get_engine, init_db


ALEMBIC_VERSION_TABLE = "alembic_version"


def _alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    return config


def _version_rows() -> list[str]:
    engine = get_engine()
    with engine.connect() as connection:
        return list(connection.execute(text(f"SELECT version_num FROM {ALEMBIC_VERSION_TABLE}")).scalars())


def main() -> None:
    engine = get_engine()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    app_tables = table_names - {ALEMBIC_VERSION_TABLE}
    config = _alembic_config()

    if ALEMBIC_VERSION_TABLE not in table_names:
        if app_tables:
            print("[local-migrate] existing local tables found without Alembic tracking; aligning schema and stamping head")
            init_db()
            command.stamp(config, "head")
            return
        print("[local-migrate] no local tables found; running Alembic migrations")
        command.upgrade(config, "head")
        return

    if not _version_rows() and app_tables:
        print("[local-migrate] empty Alembic version table with existing local tables; aligning schema and stamping head")
        init_db()
        command.stamp(config, "head")
        return

    print("[local-migrate] running Alembic migrations")
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
