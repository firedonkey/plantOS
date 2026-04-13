from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from platform_app.core.settings import get_settings


router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="platform_app/web/templates")


@router.get("/")
def index(request: Request):
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": settings.app_name,
            "version": settings.version,
        },
    )
