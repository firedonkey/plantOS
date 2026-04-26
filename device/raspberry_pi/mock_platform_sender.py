import argparse
import itertools
import threading
import time
from pathlib import Path

from config import load_config
from platform_client import (
    DEFAULT_MOCK_IMAGES,
    handle_pending_commands,
    next_sleep_seconds,
    run_command_poll_loop,
    run_status_loop,
    send_image,
    send_reading,
)
from services.automation import PlantAutomation


def main() -> None:
    parser = argparse.ArgumentParser(description="Send mock readings and mock images to PlantLab platform.")
    parser.add_argument("--config", default="config.yaml", help="Path to device config YAML.")
    parser.add_argument("--platform-url", help="Platform base URL, for example http://127.0.0.1:8000.")
    parser.add_argument("--device-id", type=int, help="Platform device id.")
    parser.add_argument("--device-token", help="Platform device API token.")
    parser.add_argument("--interval", type=int, help="Seconds between mock sends. Alias for --send-interval.")
    parser.add_argument("--send-interval", type=int, help="Seconds between mock reading uploads.")
    parser.add_argument("--command-interval", type=int, help="Seconds between command polls.")
    parser.add_argument("--status-interval", type=int, help="Seconds between mock actuator status heartbeats.")
    parser.add_argument("--once", action="store_true", help="Send one mock reading and exit.")
    parser.add_argument(
        "--image-every",
        "--image-every-n-cycles",
        dest="image_every",
        type=int,
        default=3,
        help="Upload one mock image every N cycles. Use 0 to skip.",
    )
    parser.add_argument("--skip-commands", action="store_true", help="Do not poll or acknowledge platform commands.")
    args = parser.parse_args()

    config = load_config(args.config)
    force_mock_config(config)

    platform_config = config.get("platform", {})
    platform_url = (args.platform_url or platform_config.get("url") or "http://127.0.0.1:8000").rstrip("/")
    device_id = args.device_id or platform_config.get("device_id")
    device_token = args.device_token or platform_config.get("device_token")
    send_interval = int(args.send_interval or args.interval or platform_config.get("send_interval_seconds") or 10)
    command_interval = int(args.command_interval or platform_config.get("command_poll_interval_seconds") or 2)
    status_interval = int(args.status_interval or platform_config.get("status_interval_seconds") or 10)

    if not device_id or not device_token:
        raise SystemExit("Set --device-id and --device-token, or add them under platform: in config.yaml.")

    automation = PlantAutomation(config)
    image_paths = [path for path in DEFAULT_MOCK_IMAGES if path.exists()]
    image_cycle = itertools.cycle(image_paths) if image_paths else None

    stop_event = threading.Event()
    command_thread = None
    status_thread = None
    try:
        if not args.skip_commands and not args.once:
            command_thread = threading.Thread(
                target=run_command_poll_loop,
                args=(platform_url, int(device_id), str(device_token), automation, command_interval, stop_event),
                daemon=True,
            )
            command_thread.start()
            status_thread = threading.Thread(
                target=run_status_loop,
                args=(platform_url, int(device_id), str(device_token), automation, status_interval, stop_event),
                daemon=True,
            )
            status_thread.start()

        cycle = 0
        next_send_at = 0.0
        while True:
            now = time.monotonic()
            should_send = now >= next_send_at

            if args.once and not args.skip_commands:
                handle_pending_commands(platform_url, int(device_id), str(device_token), automation)

            if should_send:
                cycle += 1
                record = automation.run_once()
                send_reading(platform_url, int(device_id), str(device_token), record)

                should_upload_image = args.image_every > 0 and cycle % args.image_every == 0
                if should_upload_image and image_cycle is not None:
                    send_image(platform_url, int(device_id), str(device_token), next(image_cycle))
                next_send_at = time.monotonic() + send_interval

            if args.once:
                break
            stop_event.wait(next_sleep_seconds(next_send_at))
    finally:
        stop_event.set()
        if command_thread is not None:
            command_thread.join(timeout=5)
        if status_thread is not None:
            status_thread.join(timeout=5)
        automation.close()


def force_mock_config(config: dict) -> None:
    config.setdefault("hardware", {})["mock_mode"] = True
    config.setdefault("camera", {})["mock_mode"] = True
    config.setdefault("sensors", {}).setdefault("dht22", {})["mock_mode"] = True
    config.setdefault("sensors", {}).setdefault("moisture", {})["mock_mode"] = True


if __name__ == "__main__":
    main()
