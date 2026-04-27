#!/usr/bin/env python3
"""PlantLab v2 Phase 1 stress test harness (serial-based).

This script drives ESP-NOW command traffic through the master node serial port,
optionally tails the camera-node serial output, and prints a summary.

Usage example:
  python scripts/phase1_stress_test.py \
    --master-port /dev/cu.usbmodem1301 \
    --camera-port /dev/cu.usbmodem12201 \
    --duration 1800
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass, field

try:
    import serial
except ImportError:  # pragma: no cover - runtime check
    print("pyserial is required. Install with: python -m pip install pyserial", file=sys.stderr)
    raise


ACK_RE = re.compile(
    r"ACK request=(?P<request>\d+)\s+command=(?P<command>[a-z_]+)\s+status=(?P<status>[a-z_]+)"
)
HEALTH_RE = re.compile(r"HEALTH request=(?P<request>\d+)\s+uptime_ms=(?P<uptime>\d+)\s+free_heap=(?P<heap>\d+)")
CAM_CAPTURE_RE = re.compile(r"captured image count=(?P<count>\d+)\s+\d+x\d+\s+(?P<bytes>\d+)\s+bytes")


@dataclass
class StressCounters:
    sent_capture: int = 0
    sent_health: int = 0
    sent_provision: int = 0

    ack_capture_ok: int = 0
    ack_capture_fail: int = 0
    ack_health_ok: int = 0
    ack_health_fail: int = 0
    ack_provision_ok: int = 0
    ack_provision_fail: int = 0

    health_reports: int = 0
    camera_capture_logs: int = 0

    last_camera_bytes: int = 0
    errors: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 1 ESP-NOW stress test.")
    parser.add_argument("--master-port", required=True, help="Master node serial port")
    parser.add_argument("--camera-port", help="Camera node serial port (optional but recommended)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--duration", type=int, default=900, help="Test duration in seconds")
    parser.add_argument("--capture-interval", type=float, default=5.0, help="Seconds between capture commands")
    parser.add_argument("--health-interval", type=float, default=3.0, help="Seconds between health commands")
    parser.add_argument(
        "--provision-interval",
        type=float,
        default=0.0,
        help="Seconds between provision_start commands (0 disables)",
    )
    parser.add_argument("--warmup", type=float, default=3.0, help="Warmup seconds before sending commands")
    parser.add_argument("--quiet", action="store_true", help="Reduce line-by-line log output")
    return parser.parse_args()


def read_lines(port: serial.Serial, limit: int = 20) -> list[str]:
    lines: list[str] = []
    for _ in range(limit):
        raw = port.readline()
        if not raw:
            break
        line = raw.decode("utf-8", errors="replace").strip()
        if line:
            lines.append(line)
    return lines


def send_command(port: serial.Serial, command: str) -> None:
    port.write(command.encode("utf-8"))
    port.flush()


def handle_master_line(line: str, counters: StressCounters) -> None:
    ack_match = ACK_RE.search(line)
    if ack_match:
        command = ack_match.group("command")
        status = ack_match.group("status")
        ok = status == "ok"
        if command == "capture_image":
            counters.ack_capture_ok += 1 if ok else 0
            counters.ack_capture_fail += 0 if ok else 1
        elif command == "health_check":
            counters.ack_health_ok += 1 if ok else 0
            counters.ack_health_fail += 0 if ok else 1
        elif command == "provision_start":
            counters.ack_provision_ok += 1 if ok else 0
            counters.ack_provision_fail += 0 if ok else 1
        return

    health_match = HEALTH_RE.search(line)
    if health_match:
        counters.health_reports += 1
        return


def handle_camera_line(line: str, counters: StressCounters) -> None:
    capture_match = CAM_CAPTURE_RE.search(line)
    if capture_match:
        counters.camera_capture_logs += 1
        counters.last_camera_bytes = int(capture_match.group("bytes"))


def print_summary(counters: StressCounters, duration_s: int) -> int:
    print("\n=== Phase 1 Stress Test Summary ===")
    print(f"Duration: {duration_s}s")
    print(f"Sent: capture={counters.sent_capture} health={counters.sent_health} provision={counters.sent_provision}")
    print(
        "ACK capture: ok={} fail={}".format(
            counters.ack_capture_ok,
            counters.ack_capture_fail,
        )
    )
    print(
        "ACK health:  ok={} fail={}".format(
            counters.ack_health_ok,
            counters.ack_health_fail,
        )
    )
    print(
        "ACK provision: ok={} fail={}".format(
            counters.ack_provision_ok,
            counters.ack_provision_fail,
        )
    )
    print(f"Health reports received: {counters.health_reports}")
    print(
        "Camera capture logs: {} (last bytes={})".format(
            counters.camera_capture_logs,
            counters.last_camera_bytes,
        )
    )

    exit_code = 0
    if counters.sent_capture > 0 and counters.ack_capture_ok < counters.sent_capture:
        print(
            "[WARN] Capture ACK count lower than sent capture commands. "
            f"sent={counters.sent_capture} ack_ok={counters.ack_capture_ok}"
        )
        exit_code = 2
    if counters.sent_health > 0 and counters.health_reports == 0:
        print("[WARN] No health reports were received.")
        exit_code = 2
    if counters.ack_capture_fail or counters.ack_health_fail or counters.ack_provision_fail:
        print("[WARN] One or more command ACK failures were reported.")
        exit_code = 2

    if counters.errors:
        print("[WARN] Runtime errors:")
        for err in counters.errors:
            print(f"  - {err}")
        exit_code = 2

    if exit_code == 0:
        print("[PASS] Stress test completed without detected protocol failures.")
    else:
        print("[CHECK] Stress test completed with warnings. Review logs above.")
    return exit_code


def main() -> int:
    args = parse_args()
    counters = StressCounters()

    master = serial.Serial(args.master_port, args.baud, timeout=0.15)
    camera = serial.Serial(args.camera_port, args.baud, timeout=0.15) if args.camera_port else None

    try:
        # Let devices settle after opening serial.
        time.sleep(args.warmup)
        master.reset_input_buffer()
        if camera:
            camera.reset_input_buffer()

        start = time.monotonic()
        end = start + args.duration
        next_capture = start
        next_health = start
        next_provision = start if args.provision_interval > 0 else float("inf")

        while time.monotonic() < end:
            now = time.monotonic()

            if now >= next_capture:
                send_command(master, "c")
                counters.sent_capture += 1
                next_capture += args.capture_interval

            if now >= next_health:
                send_command(master, "h")
                counters.sent_health += 1
                next_health += args.health_interval

            if args.provision_interval > 0 and now >= next_provision:
                send_command(master, "p")
                counters.sent_provision += 1
                next_provision += args.provision_interval

            for line in read_lines(master):
                handle_master_line(line, counters)
                if not args.quiet:
                    print(f"[master] {line}")

            if camera:
                for line in read_lines(camera):
                    handle_camera_line(line, counters)
                    if not args.quiet:
                        print(f"[camera] {line}")

            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n[stress] interrupted by user")
    except Exception as exc:  # pylint: disable=broad-except
        counters.errors.append(str(exc))
    finally:
        try:
            master.close()
        except Exception:  # pylint: disable=broad-except
            pass
        if camera:
            try:
                camera.close()
            except Exception:  # pylint: disable=broad-except
                pass

    return print_summary(counters, args.duration)


if __name__ == "__main__":
    raise SystemExit(main())

