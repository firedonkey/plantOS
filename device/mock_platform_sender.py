import argparse
import itertools
import time
from pathlib import Path

from config import load_config
from platform_client import (
    DEFAULT_MOCK_IMAGES,
    handle_pending_commands,
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
    parser.add_argument("--interval", type=int, help="Seconds between mock sends.")
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
    interval = int(args.interval or platform_config.get("send_interval_seconds") or 10)

    if not device_id or not device_token:
        raise SystemExit("Set --device-id and --device-token, or add them under platform: in config.yaml.")

    automation = PlantAutomation(config)
    image_paths = [path for path in DEFAULT_MOCK_IMAGES if path.exists()]
    image_cycle = itertools.cycle(image_paths) if image_paths else None

    try:
        cycle = 0
        while True:
            cycle += 1
            record = automation.run_once()
            send_reading(platform_url, int(device_id), str(device_token), record)

            should_upload_image = args.image_every > 0 and cycle % args.image_every == 0
            if should_upload_image and image_cycle is not None:
                send_image(platform_url, int(device_id), str(device_token), next(image_cycle))

            if not args.skip_commands:
                handled_count = handle_pending_commands(platform_url, int(device_id), str(device_token), automation)
                if handled_count:
                    status_record = automation.status_snapshot(pump_event="command_update")
                    send_reading(platform_url, int(device_id), str(device_token), status_record)

            if args.once:
                break
            time.sleep(interval)
    finally:
        automation.close()


def force_mock_config(config: dict) -> None:
    config.setdefault("hardware", {})["mock_mode"] = True
    config.setdefault("camera", {})["mock_mode"] = True
    config.setdefault("sensors", {}).setdefault("dht22", {})["mock_mode"] = True
    config.setdefault("sensors", {}).setdefault("moisture", {})["mock_mode"] = True


if __name__ == "__main__":
    main()
