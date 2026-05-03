from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path

from app.api.routes import auth, commands, device_nodes, devices, health, images, readings, status
from app.core.settings import get_settings
from app.db.session import init_db
from app.web.routes import router as web_router


APP_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version)
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    app.mount("/static", StaticFiles(directory=APP_DIR / "web/static"), name="static")
    if settings.storage_backend == "local":
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        app.mount("/data/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    app.add_event_handler("startup", init_db)
    app.include_router(auth.router)
    app.include_router(commands.router)
    app.include_router(device_nodes.router)
    app.include_router(devices.router)
    app.include_router(images.router)
    app.include_router(readings.router)
    app.include_router(status.router)
    app.include_router(health.router)
    app.include_router(web_router)
    return app


app = create_app()
