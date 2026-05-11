from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
    request_validation_exception_handler as default_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def api_error(
    status_code: int,
    code: str,
    message: str,
    *,
    details: Mapping[str, Any] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": dict(details or {}),
        },
    )


def is_api_request(request: Request) -> bool:
    return request.url.path.startswith("/api/")


def normalize_error_payload(status_code: int, detail: Any) -> dict[str, Any]:
    if isinstance(detail, Mapping):
        code = detail.get("code")
        message = detail.get("message")
        details = detail.get("details")
        if isinstance(code, str) and isinstance(message, str):
            return {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details if isinstance(details, Mapping) else {},
                }
            }

    return {
        "error": {
            "code": default_error_code(status_code),
            "message": str(detail),
            "details": {},
        }
    }


def default_error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        501: "not_supported",
        502: "upstream_error",
        503: "service_unavailable",
    }.get(status_code, "api_error")


async def api_http_exception_handler(request: Request, exc: HTTPException):
    if not is_api_request(request):
        return await default_http_exception_handler(request, exc)
    return JSONResponse(status_code=exc.status_code, content=normalize_error_payload(exc.status_code, exc.detail))


async def api_validation_exception_handler(request: Request, exc: RequestValidationError):
    if not is_api_request(request):
        return await default_validation_exception_handler(request, exc)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": {
                    "errors": jsonable_encoder(exc.errors()),
                },
            }
        },
    )
