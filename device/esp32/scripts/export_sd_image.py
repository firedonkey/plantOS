#!/usr/bin/env python3
"""Export a file from camera-node SD card over serial without removing the card."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import serial


def read_until_contains(ser: serial.Serial, needle: str, timeout_s: float) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if line:
            print(line)
        if needle in line:
            return line
    raise TimeoutError(f"Timed out waiting for '{needle}'")


def export_file(port: str, baud: int, remote_path: str, output_path: Path, timeout_s: float) -> None:
    with serial.Serial(port=port, baudrate=baud, timeout=1) as ser:
        # Give board and serial monitor a moment to settle.
        time.sleep(1.0)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        command = f"d {remote_path}\n".encode("utf-8")
        ser.write(command)

        begin_marker = f"[camera-test] DUMP_BEGIN {remote_path}"
        end_marker = f"[camera-test] DUMP_END {remote_path}"

        read_until_contains(ser, begin_marker, timeout_s=timeout_s)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        hex_lines: list[str] = []

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line.startswith("[camera-test]"):
                print(line)
                if end_marker in line:
                    break
                continue

            # Hex payload line.
            hex_lines.append(line)
        else:
            raise TimeoutError(f"Timed out waiting for '{end_marker}'")

    hex_payload = "".join(hex_lines)
    if len(hex_payload) == 0:
        raise RuntimeError("No payload data received")
    try:
        data = bytes.fromhex(hex_payload)
    except ValueError as exc:
        raise RuntimeError("Received invalid hex payload") from exc

    output_path.write_bytes(data)
    print(f"[export] wrote {len(data)} bytes to {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SD file from camera node over serial.")
    parser.add_argument("--port", required=True, help="Serial port (example: /dev/cu.usbmodem12201)")
    parser.add_argument("--path", required=True, help="Remote SD path (example: /capture_12.jpg)")
    parser.add_argument("--out", required=True, help="Local output path (example: /tmp/capture_12.jpg)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--timeout", type=float, default=20.0, help="Overall timeout in seconds")
    args = parser.parse_args()

    try:
        export_file(
            port=args.port,
            baud=args.baud,
            remote_path=args.path,
            output_path=Path(args.out),
            timeout_s=args.timeout,
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[export] failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

