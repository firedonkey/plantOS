from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models import FirmwareRelease


SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish or update one firmware release row in the configured PlantLab database.",
    )
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--node-role", required=True, choices=("master", "camera"))
    parser.add_argument("--hardware-model", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--version-code", required=True, type=int)
    parser.add_argument("--min-current-version", default=None)
    parser.add_argument("--max-current-version", default=None)
    parser.add_argument("--channel", default="stable", choices=("dev", "alpha", "beta", "stable", "local"))
    parser.add_argument("--rollout-percentage", default=100, type=int)
    parser.add_argument("--allow-hardware-device-id", action="append", default=[])
    parser.add_argument("--rollback-release-id", default=None)
    parser.add_argument("--rollback-version", default=None)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--artifact-size-bytes", required=True, type=int)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()

    if args.version_code <= 0:
        parser.error("--version-code must be positive")
    if args.artifact_size_bytes <= 0:
        parser.error("--artifact-size-bytes must be positive")
    if len(args.release_id) > 80:
        parser.error("--release-id must be 80 characters or fewer")
    if len(args.hardware_model) > 120:
        parser.error("--hardware-model must be 120 characters or fewer")
    if len(args.version) > 120:
        parser.error("--version must be 120 characters or fewer")
    if args.min_current_version and len(args.min_current_version) > 120:
        parser.error("--min-current-version must be 120 characters or fewer")
    if args.max_current_version and len(args.max_current_version) > 120:
        parser.error("--max-current-version must be 120 characters or fewer")
    if args.rollout_percentage < 0 or args.rollout_percentage > 100:
        parser.error("--rollout-percentage must be between 0 and 100")
    for hardware_device_id in args.allow_hardware_device_id:
        if len(hardware_device_id) > 120:
            parser.error("--allow-hardware-device-id values must be 120 characters or fewer")
    if args.rollback_release_id and len(args.rollback_release_id) > 80:
        parser.error("--rollback-release-id must be 80 characters or fewer")
    if args.rollback_version and len(args.rollback_version) > 120:
        parser.error("--rollback-version must be 120 characters or fewer")
    if len(args.artifact_path) > 500:
        parser.error("--artifact-path must be 500 characters or fewer")
    if not args.artifact_path.startswith("gs://"):
        parser.error("--artifact-path must be a backend-owned gs:// URI for production OTA")
    if not SHA256_PATTERN.fullmatch(args.sha256):
        parser.error("--sha256 must be a 64-character hex digest")

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        release = session.get(FirmwareRelease, args.release_id)
        if release is None:
            release = FirmwareRelease(release_id=args.release_id, created_at=now)

        release.node_role = args.node_role
        release.hardware_model = args.hardware_model
        release.version = args.version
        release.version_code = args.version_code
        release.min_current_version = args.min_current_version
        release.max_current_version = args.max_current_version
        release.channel = args.channel
        release.rollout_percentage = args.rollout_percentage
        release.allowed_hardware_device_ids = (
            json.dumps(sorted(set(args.allow_hardware_device_id))) if args.allow_hardware_device_id else None
        )
        release.rollback_release_id = args.rollback_release_id
        release.rollback_version = args.rollback_version
        release.artifact_path = args.artifact_path
        release.artifact_size_bytes = args.artifact_size_bytes
        release.sha256 = args.sha256.lower()
        release.signature = None
        release.status = "published"
        release.published_at = now

        session.add(release)
        session.commit()

    print(
        "published firmware release "
        f"release_id={args.release_id} node_role={args.node_role} version={args.version} "
        f"channel={args.channel} rollout={args.rollout_percentage}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
