from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from platform_app.core.settings import get_settings
from platform_app.db.session import SessionLocal
from platform_app.schemas.devices import DeviceCreate
from platform_app.services.devices import create_device_for_user, list_devices_for_user
from platform_app.services.users import get_user_by_id


router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="platform_app/web/templates")


@router.get("/")
def index(request: Request):
    settings = get_settings()
    current_user = None
    user_id = request.session.get("user_id")
    if user_id:
        with SessionLocal() as session:
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
def devices_page(request: Request):
    settings = get_settings()
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    with SessionLocal() as session:
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


@router.post("/devices")
async def create_device_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    device_data = DeviceCreate(
        name=str(form.get("name", "")).strip(),
        location=str(form.get("location", "")).strip() or None,
        plant_type=str(form.get("plant_type", "")).strip() or None,
    )

    with SessionLocal() as session:
        current_user = get_user_by_id(session, int(user_id))
        if current_user is None:
            request.session.clear()
            return RedirectResponse(url="/login", status_code=303)
        create_device_for_user(session, current_user, device_data)

    return RedirectResponse(url="/devices", status_code=303)
