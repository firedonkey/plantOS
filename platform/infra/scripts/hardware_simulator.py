#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


def request_json(method: str, url: str, token: str, payload: dict | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Device-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body}
        return exc.code, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Send fake PlantLab hardware data and process pending commands.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--device-token", required=True, help="Device API token")
    parser.add_argument("--hardware-device-id", default=None, help="Optional hardware node id")
    parser.add_argument("--moisture", type=float, default=42.0)
    parser.add_argument("--temperature", type=float, default=22.5)
    parser.add_argument("--humidity", type=float, default=51.0)
    parser.add_argument("--light-on", action="store_true")
    parser.add_argument("--pump-on", action="store_true")
    args = parser.parse_args()

    reading_payload = {
        "hardware_device_id": args.hardware_device_id,
        "moisture": args.moisture,
        "temperature": args.temperature,
        "humidity": args.humidity,
        "light_on": args.light_on,
        "pump_on": args.pump_on,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    status, payload = request_json("POST", f"{args.base_url}/api/hardware/readings", args.device_token, reading_payload)
    print(f"reading_upload status={status} payload={json.dumps(payload)}")
    if status >= 400:
        return 1

    status, commands = request_json("GET", f"{args.base_url}/api/hardware/commands/pending", args.device_token)
    print(f"command_poll status={status} payload={json.dumps(commands)}")
    if status >= 400:
        return 1

    for command in commands:
        result_payload = {
            "status": "completed",
            "message": f"{command['target']} {command['action']} applied by simulator",
            "light_on": True if command["target"] == "light" and command["action"] == "on" else False if command["target"] == "light" else None,
            "pump_on": False,
        }
        result_status, result = request_json(
            "POST",
            f"{args.base_url}/api/hardware/commands/{command['id']}/result",
            args.device_token,
            result_payload,
        )
        print(f"command_result status={result_status} payload={json.dumps(result)}")
        if result_status >= 400:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
