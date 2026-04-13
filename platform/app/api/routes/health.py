from fastapi import APIRouter

from app.core.settings import get_settings


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
    }
