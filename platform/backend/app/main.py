from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path

from app.api.errors import api_http_exception_handler, api_validation_exception_handler
from app.api.routes import admin, auth, commands, device_nodes, devices, firmware, hardware, health, images, readings, setup, status
from app.core.settings import get_settings
from app.db.session import init_db
from app.web.routes import router as web_router


APP_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version)
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    if settings.standalone_web_origin_regex:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=settings.standalone_web_origin_regex,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_exception_handler(HTTPException, api_http_exception_handler)
    app.add_exception_handler(RequestValidationError, api_validation_exception_handler)
    app.mount("/static", StaticFiles(directory=APP_DIR / "web/static"), name="static")
    if settings.storage_backend == "local":
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        app.mount("/data/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
    app.add_event_handler("startup", init_db)
    app.include_router(admin.router)
    app.include_router(auth.router)
    app.include_router(commands.router)
    app.include_router(device_nodes.router)
    app.include_router(devices.router)
    app.include_router(firmware.router)
    app.include_router(hardware.router)
    app.include_router(images.router)
    app.include_router(readings.router)
    app.include_router(setup.router)
    app.include_router(status.router)
    app.include_router(health.router)
    app.include_router(web_router)
    return app


app = create_app()
