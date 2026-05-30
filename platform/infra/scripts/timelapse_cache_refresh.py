#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from urllib import error, parse, request


def main() -> int:
    parser = argparse.ArgumentParser("Refresh cached PlantLab timelapse snapshots.")
    parser.add_argument("--base-url", default=os.getenv("PLANTLAB_API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--device-id", type=int, default=None, help="Optional single device id to refresh.")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--interval-minutes", type=int, default=5)
    parser.add_argument("--max-frames", type=int, default=168)
    parser.add_argument("--target-duration-seconds", type=int, default=30)
    parser.add_argument(
        "--secret",
        default=os.getenv("PLANTLAB_TIMELAPSE_REFRESH_SECRET") or os.getenv("PLANTLAB_PROVISIONING_SHARED_SECRET"),
        help="Secret sent as x-plantlab-timelapse-secret. Defaults to env.",
    )
    args = parser.parse_args()
    if not args.secret:
        raise SystemExit("Set --secret or PLANTLAB_TIMELAPSE_REFRESH_SECRET before refreshing timelapse cache.")

    params = {
        "device_id": args.device_id,
        "days": args.days,
        "interval_minutes": args.interval_minutes,
        "max_frames": args.max_frames,
        "target_duration_seconds": args.target_duration_seconds,
    }
    query = parse.urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{args.base_url.rstrip('/')}/api/admin/timelapse/refresh?{query}"
    req = request.Request(
        url,
        method="POST",
        headers={
            "Accept": "application/json",
            "x-plantlab-timelapse-secret": args.secret,
        },
    )
    try:
        with request.urlopen(req, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} refreshing timelapse cache\n{detail}") from exc
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
