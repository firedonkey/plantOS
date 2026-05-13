#!/usr/bin/env python3

from __future__ import annotations

from plantlab_local_api import auth_token, build_common_parser, print_json, request_json


def main() -> None:
    parser = build_common_parser("Inspect recent image uploads for one local PlantLab device.")
    parser.add_argument("--device-id", required=True, type=int, help="Device id to inspect.")
    parser.add_argument("--limit", default=8, type=int, help="Number of recent images to return.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    token = auth_token(base_url, email=args.email, password=args.password, token=args.token)
    payload = request_json(
        "GET",
        f"{base_url}/api/devices/{args.device_id}/images?limit={args.limit}",
        token=token,
    )
    print_json(payload)


if __name__ == "__main__":
    main()
