#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib import error, parse, request


DEFAULT_EMAIL = "dev@plantlab.local"
DEFAULT_PASSWORD = "password"


def build_common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--base-url", default="http://localhost:8000", help="PlantLab backend base URL.")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Dev login email for local API access.")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Dev login password for local API access.")
    parser.add_argument("--token", default=None, help="Optional bearer token. Skips dev login when provided.")
    return parser


def auth_token(base_url: str, *, email: str, password: str, token: str | None = None) -> str:
    if token:
        return token
    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    data = request_json(
        "POST",
        f"{base_url.rstrip('/')}/api/auth/login",
        body=payload,
        headers={"Content-Type": "application/json"},
    )
    return str(data["token"])


def request_json(method: str, url: str, *, token: str | None = None, body: bytes | None = None, headers: dict[str, str] | None = None) -> Any:
    final_headers = {"Accept": "application/json"}
    if headers:
        final_headers.update(headers)
    if token:
        final_headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, method=method.upper(), data=body, headers=final_headers)
    try:
        with request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} calling {url}\n{payload}") from exc
    except error.URLError as exc:
        raise SystemExit(f"Network error calling {url}: {exc.reason}") from exc


def format_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def print_json(payload: Any) -> None:
    sys.stdout.write(format_json(payload))
    sys.stdout.write("\n")


def url_with_query(path: str, **params: Any) -> str:
    query = parse.urlencode({key: value for key, value in params.items() if value is not None})
    return f"{path}?{query}" if query else path
