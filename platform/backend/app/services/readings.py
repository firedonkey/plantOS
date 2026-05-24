from datetime import datetime

from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.models import SensorReading
from app.schemas.readings import SensorReadingCreate


MAX_READING_QUERY_LIMIT = 50_000


def create_sensor_reading(session: Session, payload: SensorReadingCreate) -> SensorReading:
    reading = SensorReading(
        device_id=payload.device_id,
        moisture=payload.moisture,
        temperature=payload.temperature,
        humidity=payload.humidity,
        water_temperature_c=payload.water_temperature_c,
        water_level_raw=payload.water_level_raw,
        water_level_state=payload.water_level_state,
        light_on=payload.light_on,
        light_intensity_percent=payload.light_intensity_percent,
        pump_on=payload.pump_on,
        pump_status=payload.pump_status,
    )
    if payload.timestamp is not None:
        reading.timestamp = payload.timestamp

    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


def list_recent_readings_for_device(
    session: Session,
    device_id: int,
    limit: int = 50,
    since: datetime | None = None,
    until: datetime | None = None,
    order: str = "newest",
) -> list[SensorReading]:
    safe_limit = min(max(limit, 1), MAX_READING_QUERY_LIMIT)
    filters = [SensorReading.device_id == device_id]
    if since is not None:
        filters.append(SensorReading.timestamp >= since)
    if until is not None:
        filters.append(SensorReading.timestamp <= until)

    ordering = (
        (asc(SensorReading.timestamp), asc(SensorReading.id))
        if order == "oldest"
        else (desc(SensorReading.timestamp), desc(SensorReading.id))
    )

    return list(
        session.scalars(
            select(SensorReading)
            .where(*filters)
            .order_by(*ordering)
            .limit(safe_limit)
        )
    )


def get_latest_reading_for_device(session: Session, device_id: int) -> SensorReading | None:
    return session.scalar(
        select(SensorReading)
        .where(SensorReading.device_id == device_id)
        .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
        .limit(1)
    )
