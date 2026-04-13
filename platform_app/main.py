from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from platform_app.api.routes import health
from platform_app.core.settings import get_settings
from platform_app.web.routes import router as web_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version)
    app.mount("/static", StaticFiles(directory="platform_app/web/static"), name="static")
    app.include_router(health.router)
    app.include_router(web_router)
    return app


app = create_app()
