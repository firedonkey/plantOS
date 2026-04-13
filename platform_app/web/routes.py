from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from platform_app.core.settings import get_settings
from platform_app.db.session import SessionLocal
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
