from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import httpx
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_session
from app.schemas.commands import CommandCreate
from app.schemas.devices import DeviceCreate
from app.services.commands import create_command, list_commands_for_device
from app.services.devices import (
    create_device_for_user,
    delete_device_for_user,
    get_device_for_user,
    list_devices_for_user,
)
from app.services.images import list_recent_images_for_device
from app.services.readings import (
    get_latest_reading_for_device,
    list_recent_readings_for_device,
)
from app.services.storage import proxied_image_src
from app.services.users import get_user_by_id


router = APIRouter(tags=["web"])
WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=WEB_DIR / "templates")
MAX_CHART_POINTS = 60
CHART_RANGES = [
    {"key": "1h", "label": "1 hour", "title": "Last 1 hour", "delta": timedelta(hours=1)},
    {"key": "24h", "label": "24 hours", "title": "Last 24 hours", "delta": timedelta(hours=24)},
    {"key": "7d", "label": "7 days", "title": "Last 7 days", "delta": timedelta(days=7)},
    {"key": "30d", "label": "30 days", "title": "Last 30 days", "delta": timedelta(days=30)},
    {"key": "1y", "label": "1 year", "title": "Last 1 year", "delta": timedelta(days=365)},
]


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
    device_cards = [_device_overview_card(session, device) for device in devices]
    next_device_number = len(devices) + 1

    return templates.TemplateResponse(
        request,
        "devices.html",
        {
            "app_name": settings.app_name,
            "current_user": current_user,
            "device_cards": device_cards,
            "suggested_device_name": f"Device {next_device_number}",
            "suggested_plant_type": f"Plant {next_device_number}",
            "suggested_location": f"Location {next_device_number}",
        },
    )


@router.get("/devices/add")
def add_device_page(request: Request, session: Session = Depends(get_session)):
    settings = get_settings()
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    current_user = get_user_by_id(session, int(user_id))
    if current_user is None:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    devices = list_devices_for_user(session, current_user)
    next_device_number = len(devices) + 1

    return templates.TemplateResponse(
        request,
        "add_device.html",
        {
            "app_name": settings.app_name,
            "current_user": current_user,
            "suggested_device_name": f"Device {next_device_number}",
            "suggested_location": f"Location {next_device_number}",
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

    chart_range = _selected_chart_range(request.query_params.get("range"))
    since = datetime.now(timezone.utc) - chart_range["delta"]
    latest_reading = get_latest_reading_for_device(session, device.id)
    recent_readings = list_recent_readings_for_device(session, device.id, limit=2000, since=since)
    recent_images = list_recent_images_for_device(session, device.id, limit=6)
    recent_commands = list_commands_for_device(session, device.id, limit=10)
    latest_image = recent_images[0] if recent_images else None
    latest_activity = _latest_device_activity(device, latest_reading, latest_image, recent_commands)
    connection = _device_connection(latest_activity)
    reading_chart = _reading_chart(recent_readings, max_points=MAX_CHART_POINTS)
    command_activity = [_command_activity_item(command) for command in recent_commands[:8]]

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
            "command_activity": command_activity,
            "connection": connection,
            "image_src": proxied_image_src,
            "reading_chart": reading_chart,
            "chart_range": chart_range,
            "chart_ranges": CHART_RANGES,
            "active_command_keys": _active_command_keys(recent_commands),
        },
    )


@router.get("/devices/{device_id}/summary.json")
def device_summary_json(
    request: Request,
    device_id: int,
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required.")

    current_user = get_user_by_id(session, int(user_id))
    if current_user is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Sign in required.")

    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    latest_reading = get_latest_reading_for_device(session, device.id)
    recent_images = list_recent_images_for_device(session, device.id, limit=6)
    recent_commands = list_commands_for_device(session, device.id, limit=10)
    latest_image = recent_images[0] if recent_images else None
    latest_activity = _latest_device_activity(device, latest_reading, latest_image, recent_commands)
    connection = _device_connection(latest_activity)

    return JSONResponse(
        {
            "connection": connection,
            "latest_reading": _reading_summary(device, latest_reading, recent_commands),
            "latest_image": _image_summary(latest_image),
            "recent_images": [_image_summary(image) for image in recent_images],
            "command_activity": [_command_activity_item(command) for command in recent_commands[:8]],
            "active_command_keys": _active_command_keys(recent_commands),
        }
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


@router.post("/devices/setup-code")
async def create_device_setup_code_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required.")

    data = await request.json()
    serial_number = str(data.get("serial_number", "")).strip()
    if not serial_number:
        raise HTTPException(status_code=422, detail="SN is required.")

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.provisioning_api_url}/api/devices/setup-code",
                json={"serial_number": serial_number},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Provisioning service unavailable: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Provisioning service returned an invalid response.") from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=payload.get("message") or payload.get("error") or "Could not verify this SN.",
        )

    return JSONResponse(payload, status_code=response.status_code)


@router.post("/devices/{device_id}/delete")
async def delete_device_page(
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

    delete_device_for_user(session, current_user, device_id)
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
    command = create_command(session, device.id, command_data)

    if request.headers.get("x-requested-with") == "fetch":
        return JSONResponse(
            {
                "id": command.id,
                "status": _enum_value(command.status),
                "key": _command_key(command),
            },
            status_code=201,
        )

    return RedirectResponse(url=f"/devices/{device.id}", status_code=303)


def _latest_device_activity(device, latest_reading, latest_image, recent_commands: list) -> dict | None:
    activities = []
    if device.status_updated_at is not None:
        activities.append(
            {
                "timestamp": device.status_updated_at,
                "source": "status",
                "description": device.status_message or "device status",
            }
        )
    if latest_reading is not None:
        activities.append(
            {
                "timestamp": latest_reading.timestamp,
                "source": "reading",
                "description": "sensor reading",
            }
        )
    if latest_image is not None:
        activities.append(
            {
                "timestamp": latest_image.timestamp,
                "source": "image",
                "description": "camera image",
            }
        )
    for command in recent_commands:
        timestamp = command.completed_at or command.sent_at
        if timestamp is not None:
            activities.append(
                {
                    "timestamp": timestamp,
                    "source": "command",
                    "description": "command response",
                }
            )

    if not activities:
        return None

    return max(activities, key=lambda activity: _as_utc(activity["timestamp"]))


def _device_overview_card(session: Session, device) -> dict:
    latest_reading = get_latest_reading_for_device(session, device.id)
    latest_images = list_recent_images_for_device(session, device.id, limit=1)
    latest_image = latest_images[0] if latest_images else None
    recent_commands = list_commands_for_device(session, device.id, limit=5)
    latest_activity = _latest_device_activity(device, latest_reading, latest_image, recent_commands)
    connection = _device_connection(latest_activity)
    status_state = _device_status_state(device, latest_reading.timestamp if latest_reading else None)
    light_value = status_state.get("light", latest_reading.light_on if latest_reading else None)
    pump_value = status_state.get("pump", latest_reading.pump_on if latest_reading else None)

    return {
        "device": device,
        "connection": connection,
        "thumbnail_path": proxied_image_src(latest_image.id) if latest_image is not None else None,
        "moisture": _metric_value(latest_reading.moisture if latest_reading else None, "%"),
        "temperature": _metric_value(latest_reading.temperature if latest_reading else None, " C"),
        "humidity": _metric_value(latest_reading.humidity if latest_reading else None, "%"),
        "light": _bool_label(light_value),
        "pump": _bool_label(pump_value),
    }


def _reading_summary(device, reading, recent_commands: list | None = None) -> dict | None:
    if reading is None:
        if device.status_updated_at is None:
            return None
        return {
            "moisture": "n/a",
            "temperature": "n/a",
            "humidity": "n/a",
            "last_reading": device.status_updated_at.strftime("%b %-d, %-I:%M %p"),
            "light": _bool_label(device.current_light_on),
            "pump": _bool_label(device.current_pump_on),
        }
    command_state = _latest_completed_command_state(recent_commands or [], reading.timestamp)
    status_state = _device_status_state(device, reading.timestamp)
    light_value = status_state.get("light", command_state.get("light", reading.light_on))
    pump_value = status_state.get("pump", command_state.get("pump", reading.pump_on))
    return {
        "moisture": _metric_value(reading.moisture, "%"),
        "temperature": _metric_value(reading.temperature, " C"),
        "humidity": _metric_value(reading.humidity, "%"),
        "last_reading": reading.timestamp.strftime("%b %-d, %-I:%M %p"),
        "light": _bool_label(light_value),
        "pump": _bool_label(pump_value),
    }


def _device_status_state(device, since: datetime | None) -> dict[str, bool]:
    if device.status_updated_at is None:
        return {}
    if since is not None and _as_utc(device.status_updated_at) <= _as_utc(since):
        return {}

    state = {}
    if device.current_light_on is not None:
        state["light"] = device.current_light_on
    if device.current_pump_on is not None:
        state["pump"] = device.current_pump_on
    return state


def _latest_completed_command_state(commands: list, reading_timestamp: datetime) -> dict[str, bool]:
    state = {}
    reading_time = _as_utc(reading_timestamp)
    for command in sorted(commands, key=lambda item: _as_utc(item.completed_at or item.created_at), reverse=True):
        if _enum_value(command.status) != "completed" or command.completed_at is None:
            continue
        if _as_utc(command.completed_at) <= reading_time:
            continue

        target = _enum_value(command.target)
        if target == "light" and "light" not in state and command.light_on is not None:
            state["light"] = command.light_on
        if target == "pump" and "pump" not in state and command.pump_on is not None:
            state["pump"] = command.pump_on
    return state


def _image_summary(image) -> dict | None:
    if image is None:
        return None
    return {
        "src": proxied_image_src(image.id),
        "path": image.path,
        "timestamp": image.timestamp.strftime("%b %-d, %-I:%M %p"),
        "alt": "Plant capture",
    }


def _device_connection(activity: dict | None) -> dict:
    if activity is None:
        return {
            "label": "Waiting for data",
            "tone": "muted",
            "last_seen": "No readings yet",
            "source": "No device contact yet",
        }

    now = datetime.now(timezone.utc)
    timestamp = _as_utc(activity["timestamp"])
    age_seconds = max(0, int((now - timestamp).total_seconds()))
    online = age_seconds <= 90
    return {
        "label": "Online" if online else "Offline",
        "tone": "good" if online else "warning",
        "last_seen": _relative_time(age_seconds),
        "source": f"Last seen from {activity['description']}",
    }


def _as_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _metric_value(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    return f"{round(float(value), 1)}{unit}"


def _bool_label(value: bool | None) -> str:
    if value is None:
        return "n/a"
    return "on" if value else "off"


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


def _selected_chart_range(range_key: str | None) -> dict:
    for chart_range in CHART_RANGES:
        if chart_range["key"] == range_key:
            return chart_range
    return CHART_RANGES[1]


def _reading_chart(readings: list, max_points: int = MAX_CHART_POINTS) -> list[dict]:
    ordered = _sample_chart_readings(list(reversed(readings)), max_points)
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
        raw_values = [point["value"] for point in values]
        start_time = values[0]["time"] if values else None
        end_time = values[-1]["time"] if values else None
        chart.append(
            {
                **metric,
                "points": values,
                "point_count": max(len(values), 1),
                "count": len(values),
                "minimum": round(min(raw_values), 1) if raw_values else None,
                "maximum": round(max(raw_values), 1) if raw_values else None,
                "average": round(sum(raw_values) / len(raw_values), 1) if raw_values else None,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
    return chart


def _sample_chart_readings(readings: list, max_points: int) -> list:
    if max_points <= 0 or len(readings) <= max_points:
        return readings

    sampled = []
    last_index = len(readings) - 1
    sample_count = max_points - 1
    for index in range(max_points):
        source_index = round((index / sample_count) * last_index)
        sampled.append(readings[source_index])
    return sampled


def _chart_percent(value: float, min_value: float, max_value: float) -> int:
    if max_value <= min_value:
        return 0
    bounded = max(min_value, min(max_value, value))
    return round(((bounded - min_value) / (max_value - min_value)) * 100)


def _command_activity_item(command) -> dict:
    status = _enum_value(command.status)
    status_labels = {
        "pending": "Waiting",
        "sent": "Sent",
        "completed": "Done",
        "failed": "Failed",
        "timed_out": "Timed out",
    }
    status_tones = {
        "pending": "waiting",
        "sent": "sent",
        "completed": "done",
        "failed": "failed",
        "timed_out": "warning",
    }
    return {
        "label": _command_label(command),
        "key": _command_key(command),
        "status": status_labels.get(status, status.replace("_", " ").title()),
        "tone": status_tones.get(status, "waiting"),
        "message": command.message,
        "light_on": command.light_on,
        "pump_on": command.pump_on,
        "time": command.created_at.strftime("%b %-d, %-I:%M %p"),
    }


def _command_label(command) -> str:
    target = _enum_value(command.target).title()
    action = _enum_value(command.action)
    if action == "run" and command.value:
        return f"{target} run {command.value}s"
    return f"{target} {action}"


def _active_command_keys(commands: list) -> list[str]:
    return [
        _command_key(command)
        for command in commands
        if _enum_value(command.status) in {"pending", "sent"}
    ]


def _command_key(command) -> str:
    value = command.value or ""
    return f"{_enum_value(command.target)}:{_enum_value(command.action)}:{value}"


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)
