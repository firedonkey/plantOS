#!/usr/bin/env python3
"""Flash and control the PlantLab WS2811 ambient LED belt test firmware."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
FLASH_HELPER = PROJECT_DIR / "scripts" / "flash_esp32.sh"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Control the bottom PlantLab WS2811 ambient_led_belt over USB serial. "
            "This test firmware uses GPIO1 only and does not control the top grow_light panel."
        )
    )
    parser.add_argument("--port", help="Serial port, for example /dev/cu.usbmodem11301.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--build-only", action="store_true", help="Build ambient-led-belt-test firmware but do not flash.")
    parser.add_argument("--flash", action="store_true", help="Flash ambient-led-belt-test firmware before sending commands.")
    parser.add_argument("--brightness", type=int, default=3, help="Brightness 0-51. Default: 3.")
    parser.add_argument("--red", action="store_true", help="Turn the ambient LED belt dim red.")
    parser.add_argument("--green", action="store_true", help="Turn the ambient LED belt dim green.")
    parser.add_argument("--blue", action="store_true", help="Turn the ambient LED belt dim blue.")
    parser.add_argument("--white", action="store_true", help="Turn the ambient LED belt dim white.")
    parser.add_argument("--off", action="store_true", help="Turn the ambient LED belt off.")
    parser.add_argument("--walk", action="store_true", help="Run one walking-pixel pass, then turn off.")
    parser.add_argument("--chase", action="store_true", help="Run a continuous chase animation until another command.")
    parser.add_argument("--rainbow", action="store_true", help="Run a continuous rainbow animation until another command.")
    parser.add_argument("--status", action="store_true", help="Print firmware status.")
    parser.add_argument("--raw", help='Send a raw firmware command, for example: --raw "solid 255 0 0 3".')
    parser.add_argument("--interactive", action="store_true", help="Open an interactive serial command prompt.")
    return parser.parse_args()


def load_serial() -> tuple[Any, Any]:
    try:
        import serial as serial_module
        import serial.tools.list_ports as list_ports
    except ImportError as exc:  # pragma: no cover - exercised manually.
        raise SystemExit("pyserial is required. Run this with /Users/gary/plantOS/.venv/bin/python.") from exc
    return serial_module, list_ports


def detect_port() -> str:
    _, list_ports = load_serial()
    candidates = []
    for port in list_ports.comports():
        device = port.device or ""
        product = (port.product or port.description or "").lower()
        if not device.startswith("/dev/cu."):
            continue
        if "usbmodem" not in device and "usbserial" not in device:
            continue
        if "billboard" in product:
            continue
        candidates.append(port)

    esp_candidates = [
        port
        for port in candidates
        if "espressif" in (port.manufacturer or "").lower() or "303A:1001" in (port.hwid or "")
    ]
    selected = esp_candidates or candidates
    if len(selected) == 1:
        return selected[0].device
    if not selected:
        raise SystemExit("No ESP32 serial port found. Pass --port /dev/cu.<device>.")

    print("Multiple serial ports found:", file=sys.stderr)
    for port in selected:
        print(f"  {port.device}  {port.description}", file=sys.stderr)
    raise SystemExit("Pass --port explicitly.")


def run_flash_helper(mode: str, port: str | None) -> None:
    command = [str(FLASH_HELPER), "--test-ambient-led-belt", mode]
    if port:
        command.extend(["--port", port])
    subprocess.run(command, check=True)


def clamp_brightness(value: int) -> int:
    return max(0, min(51, value))


def requested_commands(args: argparse.Namespace) -> list[str]:
    brightness = clamp_brightness(args.brightness)
    commands: list[str] = []
    if args.raw:
        commands.append(args.raw)
    if args.red:
        commands.append(f"red {brightness}")
    if args.green:
        commands.append(f"green {brightness}")
    if args.blue:
        commands.append(f"blue {brightness}")
    if args.white:
        commands.append(f"white {brightness}")
    if args.walk:
        commands.append(f"walk {brightness}")
    if args.chase:
        commands.append(f"chase {brightness}")
    if args.rainbow:
        commands.append(f"rainbow {brightness}")
    if args.off:
        commands.append("off")
    if args.status:
        commands.append("status")
    return commands


def command_wait_seconds(command: str) -> float:
    if command.startswith("walk"):
        return 5.0
    return 0.9


def read_for(ser: Any, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        data = ser.read(4096)
        if data:
            sys.stdout.write(data.decode("utf-8", errors="replace"))
            sys.stdout.flush()


def send_line(ser: Any, line: str) -> None:
    print(f"> {line}")
    ser.write(f"{line}\n".encode("utf-8"))
    ser.flush()
    read_for(ser, command_wait_seconds(line))


def open_serial(port: str, baud: int) -> Any:
    serial_module, _ = load_serial()
    ser = serial_module.Serial()
    ser.port = port
    ser.baudrate = baud
    ser.timeout = 0.2
    ser.dtr = False
    ser.rts = False
    ser.open()
    ser.dtr = False
    ser.rts = False
    return ser


def main() -> int:
    args = parse_args()
    if args.flash and args.build_only:
        raise SystemExit("Choose either --flash or --build-only, not both.")

    port = args.port
    if args.flash or not args.build_only:
        port = port or detect_port()

    if args.build_only:
        run_flash_helper("--build-only", port)
        return 0

    if args.flash:
        run_flash_helper("--flash", port)
        time.sleep(1.5)

    commands = requested_commands(args)
    if not commands and not args.interactive:
        args.interactive = True

    print(f"[ambient-led-belt] opening {port} at {args.baud}")
    with open_serial(port, args.baud) as ser:
        read_for(ser, 2.0)
        for command in commands:
            send_line(ser, command)

        if args.interactive:
            print("Type commands like 'red 3', 'green 3', 'white 3', 'walk 3', 'off', or 'quit'.")
            while True:
                try:
                    line = input("> ").strip()
                except EOFError:
                    break
                if line in {"quit", "exit"}:
                    break
                if line:
                    send_line(ser, line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
