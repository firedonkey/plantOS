#!/usr/bin/env python3
"""Flash and control the PlantLab AL8860 red/white LED driver test firmware."""

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
            "Control the PlantLab AL8860 LED driver test firmware. Defaults drive AL8860 "
            "CTRL inputs: GPIO18 -> LED_RED/H1-11/U4 pin 4 for red, and GPIO8 -> "
            "LED_WHITE/H1-12/U7 pin 4 for white. The 24 V LED current path is separate. "
            "ON commands use 1 percent brightness by default."
        )
    )
    parser.add_argument("--port", help="Serial port, for example /dev/cu.usbmodem11301.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--build-only", action="store_true", help="Build led-panel-test firmware but do not flash.")
    parser.add_argument("--flash", action="store_true", help="Flash led-panel-test firmware before sending commands.")
    parser.add_argument("--red", choices=["on", "off", "toggle"], help="Set or toggle the red AL8860 CTRL channel.")
    parser.add_argument(
        "--white", choices=["on", "off", "toggle"], help="Set or toggle the white AL8860 CTRL channel."
    )
    parser.add_argument("--both", choices=["on", "off", "toggle"], help="Set or toggle both AL8860 CTRL channels.")
    parser.add_argument(
        "--brightness",
        type=int,
        default=1,
        help="Brightness percent for red/white/both ON commands and cycle. Default: 1.",
    )
    parser.add_argument(
        "--cycle",
        nargs="?",
        const=1.0,
        type=float,
        metavar="SECONDS",
        help="Run red, white, both, off sequence. Default hold is 1 second.",
    )
    parser.add_argument("--status", action="store_true", help="Print LED channel status.")
    parser.add_argument("--interactive", action="store_true", help="Keep a serial command prompt open.")
    return parser.parse_args()


def detect_port() -> str:
    _, list_ports = load_serial()
    ports = list(list_ports.comports())
    candidates = []
    for port in ports:
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
    command = [str(FLASH_HELPER), "--test-led-panel", mode]
    if port:
        command.extend(["--port", port])
    subprocess.run(command, check=True)


def clamp_percent(percent: int) -> int:
    return max(0, min(100, percent))


def command_wait_seconds(command: str) -> float:
    if command.startswith("cycle "):
        try:
            hold_ms = int(command.split()[1])
        except (IndexError, ValueError):
            hold_ms = 1000
        return max(1.0, (hold_ms / 1000.0) * 3.0 + 1.0)
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


def load_serial() -> tuple[Any, Any]:
    try:
        import serial as serial_module
        import serial.tools.list_ports as list_ports
    except ImportError as exc:  # pragma: no cover - exercised manually.
        raise SystemExit("pyserial is required. Run this with /Users/gary/plantOS/.venv/bin/python.") from exc
    return serial_module, list_ports


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

    brightness = clamp_percent(args.brightness)
    commands: list[str] = []
    single_red_on = args.red == "on" and not args.white and not args.both
    single_white_on = args.white == "on" and not args.red and not args.both
    if single_red_on or single_white_on:
        commands.append("both off")
    if args.red:
        commands.append(f"red {brightness}" if args.red == "on" else f"red {args.red}")
    if args.white:
        commands.append(f"white {brightness}" if args.white == "on" else f"white {args.white}")
    if args.both:
        commands.append(f"both {brightness}" if args.both == "on" else f"both {args.both}")
    if args.cycle is not None:
        hold_ms = max(100, min(10000, int(args.cycle * 1000)))
        commands.append(f"cycle {hold_ms} {brightness}")
    if args.status:
        commands.append("status")

    if not commands and not args.interactive:
        args.interactive = True

    print(f"[led-panel] opening {port} at {args.baud}")
    with open_serial(port, args.baud) as ser:
        read_for(ser, 2.0)
        for command in commands:
            send_line(ser, command)

        if args.interactive:
            print("Type commands like 'red on', 'white off', 'both on', 'cycle 1000', or 'quit'.")
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
