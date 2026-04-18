import argparse
import itertools
import threading
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

    stop_event = threading.Event()
    command_thread = None
    try:
        if not args.skip_commands and not args.once:
            command_thread = threading.Thread(
                target=run_command_poll_loop,
                args=(platform_url, int(device_id), str(device_token), automation, command_interval, stop_event),
                daemon=True,
            )
            command_thread.start()

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
                if should_upload_image:
                    image_path = captured_image_path(record, image_cycle if args.mock_image_fallback else None)
                    if image_path is not None:
                        send_image(platform_url, int(device_id), str(device_token), image_path)
                    else:
                        print("[platform] no camera image available to upload")
                next_send_at = time.monotonic() + send_interval

            if args.once:
                break
            stop_event.wait(next_sleep_seconds(next_send_at))
    finally:
        stop_event.set()
        if command_thread is not None:
            command_thread.join(timeout=5)
        automation.close()


def next_sleep_seconds(next_send_at: float) -> float:
    return max(0.2, min(5.0, next_send_at - time.monotonic()))


def run_command_poll_loop(
    platform_url: str,
    device_id: int,
    device_token: str,
    automation: PlantAutomation,
    command_interval: int,
    stop_event: threading.Event,
) -> None:
    print(f"[platform] command polling every {command_interval} second(s)")
    while not stop_event.is_set():
        started_at = time.monotonic()
        try:
            command_count = handle_pending_commands(platform_url, device_id, device_token, automation)
            if command_count:
                elapsed = time.monotonic() - started_at
                print(f"[platform] handled {command_count} command(s) in {elapsed:.2f}s")
        except requests.RequestException as exc:
            print(f"[platform] command poll failed: {exc}")
        except Exception as exc:
            print(f"[platform] command handling failed: {exc}")
        stop_event.wait(command_interval)


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
        command_started_at = time.monotonic()
        command_id = int(command["id"])
        try:
            message = execute_command(command, automation)
            executed_in = time.monotonic() - command_started_at
            state = command_ack_state(automation)
            ack_started_at = time.monotonic()
            acknowledge_command(
                platform_url=platform_url,
                device_id=device_id,
                device_token=device_token,
                command_id=command_id,
                status="completed",
                message=message,
                light_on=state["light_on"],
                pump_on=state["pump_on"],
            )
            acked_in = time.monotonic() - ack_started_at
            total = time.monotonic() - command_started_at
            print(
                f"[platform] command {command_id} timing: "
                f"execute={executed_in:.2f}s ack={acked_in:.2f}s total={total:.2f}s"
            )
            if command.get("target") == "pump" and command.get("action") == "run":
                schedule_pump_completion_ack(
                    platform_url=platform_url,
                    device_id=device_id,
                    device_token=device_token,
                    command_id=command_id,
                    seconds=pump_run_seconds(command, automation),
                    automation=automation,
                )
        except Exception as exc:
            state = command_ack_state(automation)
            ack_started_at = time.monotonic()
            acknowledge_command(
                platform_url=platform_url,
                device_id=device_id,
                device_token=device_token,
                command_id=command_id,
                status="failed",
                message=str(exc),
                light_on=state["light_on"],
                pump_on=state["pump_on"],
            )
            acked_in = time.monotonic() - ack_started_at
            total = time.monotonic() - command_started_at
            print(f"[platform] command {command_id} failed after {total:.2f}s; ack={acked_in:.2f}s")
    return len(commands)


def schedule_pump_completion_ack(
    platform_url: str,
    device_id: int,
    device_token: str,
    command_id: int,
    seconds: int,
    automation: PlantAutomation,
) -> None:
    thread = threading.Thread(
        target=acknowledge_pump_completion,
        args=(platform_url, device_id, device_token, command_id, seconds, automation),
        daemon=True,
    )
    thread.start()


def acknowledge_pump_completion(
    platform_url: str,
    device_id: int,
    device_token: str,
    command_id: int,
    seconds: int,
    automation: PlantAutomation,
) -> None:
    started_at = time.monotonic()
    deadline = started_at + seconds + 1
    while time.monotonic() < deadline and automation.pump.is_on:
        time.sleep(0.2)

    state = command_ack_state(automation)
    elapsed = time.monotonic() - started_at
    if state["pump_on"]:
        message = f"pump still running after {elapsed:.1f} seconds"
    elif elapsed < max(0, seconds - 0.5):
        message = f"pump stopped after {elapsed:.1f} seconds"
    else:
        message = f"pump finished after {seconds} seconds"

    try:
        acknowledge_command(
            platform_url=platform_url,
            device_id=device_id,
            device_token=device_token,
            command_id=command_id,
            status="completed",
            message=message,
            light_on=state["light_on"],
            pump_on=state["pump_on"],
        )
        print(f"[platform] pump completion status for command {command_id}: {message}")
    except requests.RequestException as exc:
        print(f"[platform] pump completion ack failed for command {command_id}: {exc}")


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
            seconds = pump_run_seconds(command, automation)
            automation.pump.run_for(seconds, wait=False)
            return f"pump started for {seconds} seconds"
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


def pump_run_seconds(command: dict, automation: PlantAutomation) -> int:
    return int(command.get("value") or automation.config["actuators"]["pump"].get("run_seconds", 5))


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
