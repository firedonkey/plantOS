from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_session
from app.schemas.commands import CommandCreate
from app.schemas.devices import DeviceCreate
from app.services.commands import create_command, list_commands_for_device
from app.services.devices import (
    create_device_for_user,
    get_device_for_user,
    list_devices_for_user,
)
from app.services.images import list_recent_images_for_device
from app.services.readings import (
    get_latest_reading_for_device,
    list_recent_readings_for_device,
)
from app.services.users import get_user_by_id


router = APIRouter(tags=["web"])
WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=WEB_DIR / "templates")


@router.get("/")
def index(request: Request, session: Session = Depends(get_session)):
    settings = get_settings()
    current_user = None
    user_id = request.session.get("user_id")
    if user_id:
        current_user = get_user_by_id(session, int(user_id))

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
            "version": settings.version,
            "current_user": current_user,
            "google_auth_configured": settings.google_auth_configured,
        },
    )


@router.get("/login")
def login_page(request: Request):
    settings = get_settings()
    user_id = request.session.get("user_id")
    if user_id:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "app_name": settings.app_name,
            "google_auth_configured": settings.google_auth_configured,
        },
    )


@router.get("/devices")
def devices_page(request: Request, session: Session = Depends(get_session)):
    settings = get_settings()
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    current_user = get_user_by_id(session, int(user_id))
    if current_user is None:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)
    devices = list_devices_for_user(session, current_user)

    return templates.TemplateResponse(
        request,
        "devices.html",
        {
            "app_name": settings.app_name,
            "current_user": current_user,
            "devices": devices,
        },
    )


@router.get("/devices/{device_id}")
def device_detail_page(
    request: Request,
    device_id: int,
    session: Session = Depends(get_session),
):
    settings = get_settings()
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    current_user = get_user_by_id(session, int(user_id))
    if current_user is None:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        return RedirectResponse(url="/devices", status_code=303)

    latest_reading = get_latest_reading_for_device(session, device.id)
    recent_readings = list_recent_readings_for_device(session, device.id, limit=10)
    recent_images = list_recent_images_for_device(session, device.id, limit=6)
    recent_commands = list_commands_for_device(session, device.id, limit=10)
    latest_image = recent_images[0] if recent_images else None
    connection = _device_connection(latest_reading.timestamp if latest_reading else None)
    reading_chart = _reading_chart(recent_readings)

    return templates.TemplateResponse(
        request,
        "device_detail.html",
        {
            "app_name": settings.app_name,
            "current_user": current_user,
            "device": device,
            "latest_reading": latest_reading,
            "recent_readings": recent_readings,
            "recent_images": recent_images,
            "latest_image": latest_image,
            "recent_commands": recent_commands,
            "connection": connection,
            "reading_chart": reading_chart,
        },
    )


@router.post("/devices")
async def create_device_page(
    request: Request,
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    device_data = DeviceCreate(
        name=str(form.get("name", "")).strip(),
        location=str(form.get("location", "")).strip() or None,
        plant_type=str(form.get("plant_type", "")).strip() or None,
    )

    current_user = get_user_by_id(session, int(user_id))
    if current_user is None:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)
    create_device_for_user(session, current_user, device_data)

    return RedirectResponse(url="/devices", status_code=303)


@router.post("/devices/{device_id}/commands")
async def create_device_command_page(
    request: Request,
    device_id: int,
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    current_user = get_user_by_id(session, int(user_id))
    if current_user is None:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        return RedirectResponse(url="/devices", status_code=303)

    form = await request.form()
    command_data = CommandCreate(
        target=str(form.get("target", "")).strip(),
        action=str(form.get("action", "")).strip(),
        value=str(form.get("value", "")).strip() or None,
    )
    create_command(session, device.id, command_data)

    return RedirectResponse(url=f"/devices/{device.id}", status_code=303)


def _device_connection(timestamp: datetime | None) -> dict:
    if timestamp is None:
        return {
            "label": "Waiting for data",
            "tone": "muted",
            "last_seen": "No readings yet",
        }

    now = datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age_seconds = max(0, int((now - timestamp).total_seconds()))
    online = age_seconds <= 90
    return {
        "label": "Online" if online else "Offline",
        "tone": "good" if online else "warning",
        "last_seen": _relative_time(age_seconds),
    }


def _relative_time(age_seconds: int) -> str:
    if age_seconds < 5:
        return "just now"
    if age_seconds < 60:
        return f"{age_seconds} seconds ago"
    minutes = age_seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


def _reading_chart(readings: list) -> list[dict]:
    ordered = list(reversed(readings[:10]))
    metrics = [
        {
            "key": "moisture",
            "label": "Moisture",
            "unit": "%",
            "min": 0,
            "max": 100,
        },
        {
            "key": "temperature",
            "label": "Temperature",
            "unit": " C",
            "min": 0,
            "max": 40,
        },
        {
            "key": "humidity",
            "label": "Humidity",
            "unit": "%",
            "min": 0,
            "max": 100,
        },
    ]
    chart = []
    for metric in metrics:
        values = []
        for reading in ordered:
            value = getattr(reading, metric["key"])
            if value is None:
                continue
            percent = _chart_percent(float(value), metric["min"], metric["max"])
            values.append(
                {
                    "value": round(float(value), 1),
                    "percent": percent,
                    "time": reading.timestamp.strftime("%-I:%M %p"),
                }
            )
        latest = values[-1]["value"] if values else None
        start_time = values[0]["time"] if values else None
        end_time = values[-1]["time"] if values else None
        chart.append(
            {
                **metric,
                "points": values,
                "latest": latest,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
    return chart


def _chart_percent(value: float, min_value: float, max_value: float) -> int:
    if max_value <= min_value:
        return 0
    bounded = max(min_value, min(max_value, value))
    return round(((bounded - min_value) / (max_value - min_value)) * 100)
