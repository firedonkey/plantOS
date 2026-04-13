from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SensorReading
from app.schemas.readings import SensorReadingCreate


def create_sensor_reading(session: Session, payload: SensorReadingCreate) -> SensorReading:
    reading = SensorReading(
        device_id=payload.device_id,
        moisture=payload.moisture,
        temperature=payload.temperature,
        humidity=payload.humidity,
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
) -> list[SensorReading]:
    return list(
        session.scalars(
            select(SensorReading)
            .where(SensorReading.device_id == device_id)
            .order_by(SensorReading.timestamp.desc())
            .limit(limit)
        )
    )


def get_latest_reading_for_device(session: Session, device_id: int) -> SensorReading | None:
    return session.scalar(
        select(SensorReading)
        .where(SensorReading.device_id == device_id)
        .order_by(SensorReading.timestamp.desc())
        .limit(1)
    )
