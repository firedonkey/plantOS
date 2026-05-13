#!/usr/bin/env python3

from __future__ import annotations

from plantlab_local_api import auth_token, build_common_parser, print_json, request_json


def main() -> None:
    parser = build_common_parser("Fetch a device summary from the local PlantLab backend.")
    parser.add_argument("--device-id", required=True, type=int, help="Device id to inspect.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    token = auth_token(base_url, email=args.email, password=args.password, token=args.token)
    payload = request_json("GET", f"{base_url}/api/devices/{args.device_id}/summary", token=token)
    print_json(payload)


if __name__ == "__main__":
    main()
