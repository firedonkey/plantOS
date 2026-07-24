#!/usr/bin/env python3
"""Capture one JPEG from a PlantLab camera node over USB serial."""

from __future__ import annotations

import argparse
import glob
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import serial


REPO_ROOT = Path(__file__).resolve().parents[3]
FLASH_HELPER = REPO_ROOT / "device" / "esp32" / "scripts" / "flash_esp32.sh"
BEGIN_RE = re.compile(rb"\[camera-node\] LOCAL_JPEG_BEGIN bytes=(\d+) width=(\d+) height=(\d+)")
END_MARKER = b"[camera-node] LOCAL_JPEG_END"


def default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path.home() / "Desktop" / f"plantlab_camera_capture_{timestamp}.jpg"


def detect_port() -> str:
    candidates = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*"))
    candidates = [port for port in candidates if "SN23456789" not in Path(port).name]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RuntimeError("No ESP32 serial port found. Pass --port /dev/cu.usbmodemXXXX.")
    joined = "\n  ".join(candidates)
    raise RuntimeError(f"Multiple ESP32 serial ports found. Pass --port explicitly:\n  {joined}")


def run_flash_helper(mode: str, port: str) -> None:
    command = [str(FLASH_HELPER), "--test-camera-platform", "--port", port, mode]
    print(f"[camera-local] running: {' '.join(command)}")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def read_line_until_begin(ser: serial.Serial, timeout_s: float) -> tuple[int, int, int]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = ser.readline()
        if not line:
            continue
        match = BEGIN_RE.search(line)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
        text = line.decode("utf-8", errors="replace").strip()
        if text:
            print(text)
    raise TimeoutError("Timed out waiting for LOCAL_JPEG_BEGIN. Is camera firmware updated?")


def read_exact(ser: serial.Serial, length: int, timeout_s: float) -> bytes:
    deadline = time.time() + timeout_s
    chunks: list[bytes] = []
    remaining = length
    while remaining > 0 and time.time() < deadline:
        chunk = ser.read(remaining)
        if not chunk:
            continue
        chunks.append(chunk)
        remaining -= len(chunk)
    data = b"".join(chunks)
    if len(data) != length:
        raise TimeoutError(f"Timed out receiving JPEG bytes: got {len(data)} of {length}")
    return data


def read_until_end(ser: serial.Serial, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = ser.readline()
        if END_MARKER in line:
            return
        text = line.decode("utf-8", errors="replace").strip()
        if text:
            print(text)
    raise TimeoutError("Timed out waiting for LOCAL_JPEG_END")


def capture_to_file(port: str, baud: int, output_path: Path, timeout_s: float, settle_s: float) -> None:
    with serial.Serial(port=port, baudrate=baud, timeout=0.25) as ser:
        print(f"[camera-local] opening {port} at {baud}")
        time.sleep(settle_s)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(b"camera local-capture\n")
        ser.flush()

        length, width, height = read_line_until_begin(ser, timeout_s)
        print(f"[camera-local] receiving JPEG {width}x{height} {length} bytes")
        data = read_exact(ser, length, timeout_s)
        read_until_end(ser, timeout_s)

    if not data.startswith(b"\xff\xd8"):
        raise RuntimeError("Received data does not start with a JPEG SOI marker")
    if not data.endswith(b"\xff\xd9"):
        raise RuntimeError("Received data does not end with a JPEG EOI marker")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    print(f"[camera-local] wrote {len(data)} bytes to {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture one local JPEG from a PlantLab camera over USB serial.")
    parser.add_argument("--port", help="Serial port, for example /dev/cu.usbmodem112201.")
    parser.add_argument("--out", type=Path, default=default_output_path(), help="Local JPEG output path.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate. Default: 115200.")
    parser.add_argument("--timeout", type=float, default=35.0, help="Timeout in seconds for capture transfer.")
    parser.add_argument("--settle", type=float, default=5.0, help="Seconds to wait after opening the serial port.")
    parser.add_argument("--flash", action="store_true", help="Flash camera-platform-test firmware before capture.")
    parser.add_argument("--build-only", action="store_true", help="Build camera-platform-test firmware and exit.")
    args = parser.parse_args()

    try:
        port = args.port or detect_port()
        if args.build_only:
            run_flash_helper("--build-only", port)
            return 0
        if args.flash:
            run_flash_helper("--flash", port)
            time.sleep(2.0)
        capture_to_file(port, args.baud, args.out, args.timeout, args.settle)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[camera-local] failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
