#!/usr/bin/env python3

from __future__ import annotations

import json

from plantlab_local_api import build_common_parser, request_json


def main() -> None:
    parser = build_common_parser("Check local backend health and local dev auth reachability.")
    parser.add_argument("--include-dev-login", action="store_true", help="Also verify dev login succeeds.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    payload = {"health": request_json("GET", f"{base_url}/health")}

    if args.include_dev_login:
        login = request_json(
            "POST",
            f"{base_url}/api/auth/login",
            body=json.dumps({"email": args.email, "password": args.password}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        payload["dev_login"] = {
            "email": login.get("email"),
            "mode": login.get("mode"),
            "user_id": login.get("user", {}).get("id"),
        }

    from plantlab_local_api import print_json

    print_json(payload)


if __name__ == "__main__":
    main()
