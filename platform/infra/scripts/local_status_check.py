#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from plantlab_local_api import auth_token, build_common_parser, request_json


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


@dataclass
class CheckResult:
    level: str
    label: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = build_common_parser("Run a one-command local PlantLab status check.")
    parser.add_argument("--device-id", type=int, default=None, help="Device id to inspect. Defaults to the first device in the account.")
    parser.add_argument("--reading-limit", type=int, default=5, help="How many recent readings to inspect.")
    parser.add_argument("--image-limit", type=int, default=5, help="How many recent images to inspect.")
    parser.add_argument("--command-limit", type=int, default=5, help="How many recent commands to inspect.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    checks: list[CheckResult] = []
    exit_code = 0

    try:
        health = request_json("GET", f"{base_url}/health")
    except SystemExit as exc:
        print_check(CheckResult(FAIL, "backend health", str(exc)))
        raise

    checks.append(
        CheckResult(
            PASS if health.get("status") == "ok" else FAIL,
            "backend health",
            f"{health.get('app', 'backend')} status={health.get('status')} version={health.get('version')}",
        )
    )

    token = auth_token(base_url, email=args.email, password=args.password, token=args.token)
    checks.append(CheckResult(PASS, "dev login", f"Authenticated as {args.email}"))

    devices = request_json("GET", f"{base_url}/api/devices", token=token)
    if not isinstance(devices, list):
        checks.append(CheckResult(FAIL, "device list", "Unexpected /api/devices response shape."))
        print_report(checks)
        raise SystemExit(1)
    if not devices:
        checks.append(CheckResult(WARN, "device list", "No devices are available in the current account."))
        print_report(checks)
        raise SystemExit(0)

    selected = pick_device(devices, args.device_id)
    if selected is None:
        checks.append(CheckResult(FAIL, "device select", f"Device {args.device_id} was not found in the current account."))
        print_report(checks)
        raise SystemExit(1)

    device_id = int(selected["id"])
    checks.append(CheckResult(PASS, "device select", f"Using device {device_id} ({selected.get('name') or 'unnamed'})"))

    summary = request_json("GET", f"{base_url}/api/devices/{device_id}/summary", token=token)
    checks.append(CheckResult(PASS, "device summary", "Summary endpoint responded successfully."))

    readings = request_json("GET", f"{base_url}/api/devices/{device_id}/readings?limit={args.reading_limit}", token=token)
    images = request_json("GET", f"{base_url}/api/devices/{device_id}/images?limit={args.image_limit}", token=token)
    commands = request_json("GET", f"{base_url}/api/devices/{device_id}/commands?limit={args.command_limit}", token=token)

    checks.extend(check_hardware_health(summary))
    checks.extend(check_recent_readings(readings))
    checks.extend(check_recent_images(summary, images))
    checks.extend(check_command_queue(commands))

    for check in checks:
        print_check(check)
        if check.level == FAIL:
            exit_code = 1

    raise SystemExit(exit_code)


def pick_device(devices: list[dict[str, Any]], requested_id: int | None) -> dict[str, Any] | None:
    if requested_id is None:
        return devices[0]
    return next((device for device in devices if int(device["id"]) == requested_id), None)


def check_hardware_health(summary: dict[str, Any]) -> list[CheckResult]:
    health = summary.get("hardware_health") or {}
    overall = str(health.get("overall_status") or "unknown")
    heartbeat = str(health.get("heartbeat_status") or "unknown")
    reading = str(health.get("reading_status") or "unknown")
    image = str(health.get("image_status") or "n/a")
    camera = str(health.get("camera_status") or "n/a")

    return [
        classify(
            "hardware health",
            {
                "online": PASS,
                "degraded": WARN,
                "warning": WARN,
                "stale": WARN,
                "offline": FAIL,
                "unknown": WARN,
            }.get(overall, WARN),
            f"overall={overall} heartbeat={heartbeat} reading={reading} image={image} camera={camera}",
        ),
        classify(
            "master node",
            level_from_status(str(health.get("master_status") or "unknown"), none_level=WARN),
            describe_node(health.get("primary")),
        ),
        classify(
            "last heartbeat",
            level_from_status(heartbeat, none_level=WARN),
            describe_timestamp("heartbeat", health.get("last_heartbeat_at")),
        ),
    ]


def check_recent_readings(readings: list[dict[str, Any]]) -> list[CheckResult]:
    if not readings:
        return [CheckResult(WARN, "recent readings", "No recent readings returned.")]
    latest = readings[0]
    age = age_from_iso(latest.get("timestamp"))
    level = PASS if age is not None and age <= timedelta(minutes=2) else WARN
    return [
        CheckResult(
            level,
            "recent readings",
            f"{len(readings)} reading(s); latest at {latest.get('timestamp')} ({format_age(age)})",
        )
    ]


def check_recent_images(summary: dict[str, Any], images: list[dict[str, Any]]) -> list[CheckResult]:
    health = summary.get("hardware_health") or {}
    camera_status = health.get("camera_status")
    if not images:
        if camera_status in {None, "n/a"}:
            return [CheckResult(PASS, "recent images", "No camera nodes reported, so no image uploads are expected.")]
        return [CheckResult(WARN, "recent images", f"No recent images returned while camera_status={camera_status}.")]

    latest = images[0]
    age = age_from_iso(latest.get("timestamp"))
    level = PASS if age is not None and age <= timedelta(minutes=5) else WARN
    return [
        CheckResult(
            level,
            "recent images",
            f"{len(images)} image(s); latest at {latest.get('timestamp')} ({format_age(age)})",
        )
    ]


def check_command_queue(commands: list[dict[str, Any]]) -> list[CheckResult]:
    if not commands:
        return [CheckResult(PASS, "command queue", "No recent commands in the queue.")]

    active = [command for command in commands if command.get("status") in {"pending", "sent", "in_progress"}]
    failed = [command for command in commands if command.get("status") in {"failed", "timed_out"}]
    latest = commands[0]

    if active:
        return [
            CheckResult(
                WARN,
                "command queue",
                f"{len(active)} active command(s); latest={latest.get('target')}:{latest.get('action')} status={latest.get('status')}",
            )
        ]
    if failed:
        latest_failed = failed[0]
        return [
            CheckResult(
                WARN,
                "command queue",
                f"Latest failed command {latest_failed.get('target')}:{latest_failed.get('action')} reason={latest_failed.get('message') or 'n/a'}",
            )
        ]
    return [
        CheckResult(
            PASS,
            "command queue",
            f"{len(commands)} recent command(s); latest={latest.get('target')}:{latest.get('action')} status={latest.get('status')}",
        )
    ]


def level_from_status(status: str, *, none_level: str = WARN) -> str:
    normalized = (status or "").lower()
    if normalized == "online":
        return PASS
    if normalized in {"stale", "warning", "unknown"}:
        return WARN
    if normalized == "offline":
        return FAIL
    return none_level


def classify(label: str, level: str, message: str) -> CheckResult:
    return CheckResult(level, label, message)


def describe_timestamp(label: str, value: Any) -> str:
    age = age_from_iso(value)
    if not value:
        return f"No {label} timestamp available."
    return f"Last {label} at {value} ({format_age(age)})"


def describe_node(node: Any) -> str:
    if not isinstance(node, dict) or not node:
        return "No primary hardware node metadata available."
    hardware_id = node.get("hardware_device_id") or node.get("hardware_id") or "unknown-hardware-id"
    status = node.get("health_status") or node.get("status") or "unknown"
    role = node.get("node_role") or node.get("role") or "unknown-role"
    last_seen = node.get("last_seen_at")
    suffix = f"; last_seen={last_seen}" if last_seen else ""
    return f"{role} {hardware_id} status={status}{suffix}"


def age_from_iso(value: Any) -> timedelta | None:
    if not value or not isinstance(value, str):
        return None
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)


def format_age(age: timedelta | None) -> str:
    if age is None:
        return "age unknown"
    seconds = max(int(age.total_seconds()), 0)
    if seconds < 60:
        return f"{seconds}s ago"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s ago"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m ago"


def print_check(check: CheckResult) -> None:
    print(f"[{check.level}] {check.label}: {check.message}")


def print_report(checks: list[CheckResult]) -> None:
    for check in checks:
        print_check(check)


if __name__ == "__main__":
    main()
