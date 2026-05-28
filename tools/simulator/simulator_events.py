from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)


class SimulatorApiError(RuntimeError):
    def __init__(self, method: str, path: str, status: int | None, message: str) -> None:
        super().__init__(f"{method} {path} failed: {status or 'network'} {message}")
        self.method = method
        self.path = path
        self.status = status
        self.message = message


class SimulatorApiClient:
    """Small standard-library JSON client for firmware-like backend calls."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_json(self, path: str, *, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = urllib.parse.urlencode(_clean_params(params or {}))
        suffix = f"?{query}" if query else ""
        request = urllib.request.Request(
            f"{self.base_url}{path}{suffix}",
            headers=self._headers(token),
            method="GET",
        )
        return self._send_json("GET", path, request)

    def post_json(self, path: str, payload: dict[str, Any], *, token: str) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={**self._headers(token), "Content-Type": "application/json"},
            method="POST",
        )
        return self._send_json("POST", path, request)

    def post_multipart(
        self,
        path: str,
        *,
        token: str,
        fields: dict[str, Any],
        files: list["MultipartFile"],
    ) -> dict[str, Any]:
        boundary = f"PlantLabSimulator{uuid4().hex}"
        body = _multipart_body(boundary, fields, files)
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                **self._headers(token),
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
            method="POST",
        )
        return self._send_json("POST", path, request)

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": "PlantLab-Simulator/1.0",
            "X-Device-Token": token,
        }

    def _send_json(self, method: str, path: str, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SimulatorApiError(method, path, exc.code, detail) from exc
        except urllib.error.URLError as exc:
            raise SimulatorApiError(method, path, None, str(exc.reason)) from exc
        except (OSError, TimeoutError) as exc:
            raise SimulatorApiError(method, path, None, str(exc)) from exc

        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SimulatorApiError(method, path, None, f"invalid JSON response: {raw[:120]}") from exc
        if not isinstance(parsed, dict):
            return {"value": parsed}
        return parsed


def _clean_params(params: dict[str, Any]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        clean[key] = str(value)
    return clean


@dataclass(frozen=True, slots=True)
class MultipartFile:
    field_name: str
    filename: str
    content_type: str
    data: bytes


def _multipart_body(boundary: str, fields: dict[str, Any], files: list[MultipartFile]) -> bytes:
    chunks: list[bytes] = []
    boundary_bytes = boundary.encode("ascii")
    for name, value in fields.items():
        if value is None:
            continue
        chunks.extend(
            [
                b"--" + boundary_bytes + b"\r\n",
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    for item in files:
        chunks.extend(
            [
                b"--" + boundary_bytes + b"\r\n",
                (
                    f'Content-Disposition: form-data; name="{item.field_name}"; '
                    f'filename="{item.filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {item.content_type}\r\n\r\n".encode("utf-8"),
                item.data,
                b"\r\n",
            ]
        )
    chunks.extend([b"--" + boundary_bytes + b"--\r\n"])
    return b"".join(chunks)
