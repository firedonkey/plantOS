from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from platform_app.api.routes import auth, health
from platform_app.core.settings import get_settings
from platform_app.db.session import init_db
from platform_app.web.routes import router as web_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version)
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    app.mount("/static", StaticFiles(directory="platform_app/web/static"), name="static")
    app.add_event_handler("startup", init_db)
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(web_router)
    return app


app = create_app()
