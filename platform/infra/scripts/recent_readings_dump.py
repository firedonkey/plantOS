#!/usr/bin/env python3

from __future__ import annotations

from plantlab_local_api import auth_token, build_common_parser, print_json, request_json, url_with_query


def main() -> None:
    parser = build_common_parser("Dump recent sensor readings for one local PlantLab device.")
    parser.add_argument("--device-id", required=True, type=int, help="Device id to inspect.")
    parser.add_argument("--limit", default=10, type=int, help="Number of readings to return.")
    parser.add_argument("--order", default="newest", choices=("newest", "oldest"), help="Reading order.")
    parser.add_argument("--start", default=None, help="Optional ISO timestamp lower bound.")
    parser.add_argument("--end", default=None, help="Optional ISO timestamp upper bound.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    token = auth_token(base_url, email=args.email, password=args.password, token=args.token)
    path = url_with_query(
        f"{base_url}/api/devices/{args.device_id}/readings",
        limit=args.limit,
        order=args.order,
        start=args.start,
        end=args.end,
    )
    payload = request_json("GET", path, token=token)
    print_json(payload)


if __name__ == "__main__":
    main()
