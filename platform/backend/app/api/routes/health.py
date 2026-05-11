from fastapi import APIRouter

from app.core.settings import get_settings


router = APIRouter(tags=["health"])


@router.get("/api/health")
@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
    }
