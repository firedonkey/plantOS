import argparse
import itertools
import time
from pathlib import Path

import requests

from config import load_config
from services.automation import PlantAutomation


DEFAULT_MOCK_IMAGES = [
    Path("dashboard/static/mock/rose-01-seedling.jpg"),
    Path("dashboard/static/mock/rose-02-young-leaves.jpg"),
    Path("dashboard/static/mock/rose-03-bud.jpg"),
    Path("dashboard/static/mock/rose-04-bloom.jpg"),
    Path("dashboard/static/mock/rose-05-bloom.jpg"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Send Raspberry Pi readings, images, and command acknowledgements to PlantLab platform.")
    parser.add_argument("--config", default="config.yaml", help="Path to device config YAML.")
    parser.add_argument("--platform-url", help="Platform base URL, for example http://127.0.0.1:8000.")
    parser.add_argument("--device-id", type=int, help="Platform device id.")
    parser.add_argument("--device-token", help="Platform device API token.")
    parser.add_argument("--interval", type=int, help="Seconds between sensor sends. Alias for --send-interval.")
    parser.add_argument("--send-interval", type=int, help="Seconds between sensor reading uploads.")
    parser.add_argument("--command-interval", type=int, help="Seconds between command polls.")
    parser.add_argument("--once", action="store_true", help="Send one reading and exit.")
    parser.add_argument(
        "--image-every",
        "--image-every-n-cycles",
        dest="image_every",
        type=int,
        default=3,
        help="Upload one image every N cycles. Use 0 to skip.",
    )
    parser.add_argument("--mock-image-fallback", action="store_true", help="Upload bundled mock images when no camera image is captured.")
    parser.add_argument("--skip-commands", action="store_true", help="Do not poll or acknowledge platform commands.")
    args = parser.parse_args()

    config = load_config(args.config)
    platform_config = config.get("platform", {})
    platform_url = (args.platform_url or platform_config.get("url") or "http://127.0.0.1:8000").rstrip("/")
    device_id = args.device_id or platform_config.get("device_id")
    device_token = args.device_token or platform_config.get("device_token")
    send_interval = int(args.send_interval or args.interval or platform_config.get("send_interval_seconds") or 10)
    command_interval = int(args.command_interval or platform_config.get("command_poll_interval_seconds") or 2)

    if not device_id or not device_token:
        raise SystemExit("Set --device-id and --device-token, or add them under platform: in config.yaml.")

    automation = PlantAutomation(config)
    image_paths = [path for path in DEFAULT_MOCK_IMAGES if path.exists()]
    image_cycle = itertools.cycle(image_paths) if image_paths else None

    try:
        cycle = 0
        next_send_at = 0.0
        next_command_poll_at = 0.0
        while True:
            now = time.monotonic()
            should_send = now >= next_send_at
            should_poll_commands = not args.skip_commands and now >= next_command_poll_at

            if should_send:
                cycle += 1
                record = automation.run_once()
                send_reading(platform_url, int(device_id), str(device_token), record)

                should_upload_image = args.image_every > 0 and cycle % args.image_every == 0
                if should_upload_image:
                    image_path = captured_image_path(record, image_cycle if args.mock_image_fallback else None)
                    if image_path is not None:
                        send_image(platform_url, int(device_id), str(device_token), image_path)
                    else:
                        print("[platform] no camera image available to upload")
                next_send_at = time.monotonic() + send_interval

            if should_poll_commands:
                handle_pending_commands(platform_url, int(device_id), str(device_token), automation)
                next_command_poll_at = time.monotonic() + command_interval

            if args.once:
                break
            time.sleep(next_sleep_seconds(next_send_at, next_command_poll_at, args.skip_commands))
    finally:
        automation.close()


def next_sleep_seconds(next_send_at: float, next_command_poll_at: float, skip_commands: bool) -> float:
    next_times = [next_send_at]
    if not skip_commands:
        next_times.append(next_command_poll_at)
    next_due_at = min(next_times)
    return max(0.2, min(5.0, next_due_at - time.monotonic()))


def send_reading(platform_url: str, device_id: int, device_token: str, record: dict) -> None:
    payload = {
        "device_id": device_id,
        "timestamp": record.get("timestamp"),
        "temperature": record.get("temperature_c"),
        "humidity": record.get("humidity_percent"),
        "moisture": record.get("moisture_percent"),
        "light_on": record.get("light_on"),
        "pump_on": record.get("pump_on"),
        "pump_status": record.get("pump_event"),
    }
    response = requests.post(
        f"{platform_url}/api/data",
        json=payload,
        headers={"X-Device-Token": device_token},
        timeout=10,
    )
    response.raise_for_status()
    print(f"[platform] sent reading: {response.json()}")


def captured_image_path(record: dict, fallback_cycle) -> Path | None:
    image_path = record.get("image_path")
    if image_path:
        path = Path(str(image_path))
        if path.exists():
            return path
        print(f"[platform] captured image path does not exist: {path}")

    if fallback_cycle is not None:
        return next(fallback_cycle)
    return None


def send_image(platform_url: str, device_id: int, device_token: str, image_path: Path) -> None:
    with image_path.open("rb") as image_file:
        response = requests.post(
            f"{platform_url}/api/image",
            data={"device_id": str(device_id)},
            files={"file": (image_path.name, image_file, "image/jpeg")},
            headers={"X-Device-Token": device_token},
            timeout=20,
        )
    response.raise_for_status()
    print(f"[platform] uploaded image: {response.json()}")


def handle_pending_commands(
    platform_url: str,
    device_id: int,
    device_token: str,
    automation: PlantAutomation,
) -> int:
    commands = poll_pending_commands(platform_url, device_id, device_token)
    for command in commands:
        try:
            message = execute_command(command, automation)
            state = command_ack_state(automation)
            acknowledge_command(
                platform_url=platform_url,
                device_id=device_id,
                device_token=device_token,
                command_id=int(command["id"]),
                status="completed",
                message=message,
                light_on=state["light_on"],
                pump_on=state["pump_on"],
            )
        except Exception as exc:
            state = command_ack_state(automation)
            acknowledge_command(
                platform_url=platform_url,
                device_id=device_id,
                device_token=device_token,
                command_id=int(command["id"]),
                status="failed",
                message=str(exc),
                light_on=state["light_on"],
                pump_on=state["pump_on"],
            )
    return len(commands)


def poll_pending_commands(platform_url: str, device_id: int, device_token: str) -> list[dict]:
    response = requests.get(
        f"{platform_url}/api/devices/{device_id}/commands/pending",
        headers={"X-Device-Token": device_token},
        timeout=10,
    )
    response.raise_for_status()
    commands = response.json()
    if commands:
        print(f"[platform] received {len(commands)} command(s)")
    return commands


def execute_command(command: dict, automation: PlantAutomation) -> str:
    target = command.get("target")
    action = command.get("action")
    value = command.get("value")

    if target == "pump":
        if action == "run":
            seconds = int(value or automation.config["actuators"]["pump"].get("run_seconds", 5))
            automation.pump.run_for(seconds)
            return f"pump ran for {seconds} seconds"
        if action == "off":
            automation.pump.off()
            return "pump turned off"

    if target == "light":
        if action == "on":
            automation.set_light(True)
            return "light turned on"
        if action == "off":
            automation.set_light(False)
            return "light turned off"

    raise ValueError(f"Unsupported command: target={target}, action={action}")


def command_ack_state(automation: PlantAutomation) -> dict:
    return {
        "light_on": automation.light.is_on,
        "pump_on": automation.pump.is_on,
    }


def acknowledge_command(
    platform_url: str,
    device_id: int,
    device_token: str,
    command_id: int,
    status: str,
    message: str,
    light_on: bool | None = None,
    pump_on: bool | None = None,
) -> None:
    response = requests.post(
        f"{platform_url}/api/devices/{device_id}/commands/{command_id}/ack",
        json={
            "status": status,
            "message": message,
            "light_on": light_on,
            "pump_on": pump_on,
        },
        headers={"X-Device-Token": device_token},
        timeout=10,
    )
    response.raise_for_status()
    print(f"[platform] acknowledged command {command_id}: {status} - {message}")


if __name__ == "__main__":
    main()
