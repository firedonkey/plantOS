from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models import Command, CommandAction, CommandStatus, CommandTarget, Device, Event, EventType, Image, SensorReading, User


def test_sqlite_models_create_and_query():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(email="grower@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)

        device = Device(
            user_id=user.id,
            name="Kitchen Rose",
            location="Kitchen window",
            plant_type="Rose",
        )
        session.add(device)
        session.commit()
        session.refresh(device)

        reading = SensorReading(
            device_id=device.id,
            moisture=41.5,
            temperature=22.4,
            humidity=53.0,
            light_on=True,
            pump_on=False,
            pump_status="not_needed",
        )
        event = Event(device_id=device.id, type=EventType.PUMP, value="not_needed")
        command = Command(
            device_id=device.id,
            target=CommandTarget.PUMP,
            action=CommandAction.RUN,
            status=CommandStatus.PENDING,
        )
        image = Image(device_id=device.id, path="data/images/plant.jpg")
        session.add(reading)
        session.add(event)
        session.add(command)
        session.add(image)
        session.commit()

        saved_device = session.scalar(select(Device).where(Device.name == "Kitchen Rose"))
        assert saved_device.owner.email == "grower@example.com"
        assert len(saved_device.readings) == 1
        assert saved_device.readings[0].moisture == 41.5
        assert saved_device.readings[0].light_on is True
        assert saved_device.readings[0].pump_on is False
        assert saved_device.readings[0].pump_status == "not_needed"
        assert saved_device.commands[0].target == CommandTarget.PUMP
        assert saved_device.events[0].type == EventType.PUMP
        assert saved_device.images[0].path == "data/images/plant.jpg"
