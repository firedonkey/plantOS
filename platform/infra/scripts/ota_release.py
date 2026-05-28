#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
ESP32_DIR = ROOT_DIR / "device" / "esp32"
FIRMWARE_VERSION_HEADER = ESP32_DIR / "include" / "firmware_version.h"
PIO_BIN = ROOT_DIR / ".venv" / "bin" / "pio"
PIO_CORE_DIR = ROOT_DIR / ".pio-core"
INFRA_ENV_FILE = ROOT_DIR / "platform" / "infra" / "env" / ".env"

PLATFORM_CONTAINER = "plantlab-local-platform"
POSTGRES_CONTAINER = "plantlab-local-postgres"
POSTGRES_USER = "plantlab_user"
POSTGRES_DB = "plantlab"
CONTAINER_FIRMWARE_DIR = "/app/platform/backend/data/firmware"

DEFAULT_PROJECT_ID = "plantlab-493805"
DEFAULT_REGION = "us-central1"
DEFAULT_SERVICE_NAME = "plantlab-api"
DEFAULT_AR_REPO = "plantlab-repo"
DEFAULT_BUCKET_NAME = "plantlab-images-garylu"
DEFAULT_DB_NAME = "plantlab"
DEFAULT_DB_USER = "plantlab_user"
DEFAULT_CLOUD_SQL_CONNECTION_NAME = "plantlab-493805:us-central1:plantlab"
DEFAULT_FIRMWARE_PREFIX = "firmware"
DEFAULT_GCP_JOB_NAME = "plantlab-firmware-release-publish"


@dataclass(frozen=True)
class OtaTarget:
    name: str
    node_role: str
    hardware_model: str
    pio_env: str
    version_symbol: str
    version_code_symbol: str

    @property
    def firmware_path(self) -> Path:
        return ESP32_DIR / ".pio" / "build" / self.pio_env / "firmware.bin"


@dataclass(frozen=True)
class FirmwareInfo:
    version: str
    version_code: int


TARGETS = {
    "master": OtaTarget(
        name="master",
        node_role="master",
        hardware_model="esp32_master",
        pio_env="esp32-local",
        version_symbol="kMasterSoftwareVersion",
        version_code_symbol="kMasterSoftwareVersionCode",
    ),
    "camera": OtaTarget(
        name="camera",
        node_role="camera",
        hardware_model="xiao_esp32s3_camera",
        pio_env="camera-platform-test",
        version_symbol="kCameraSoftwareVersion",
        version_code_symbol="kCameraSoftwareVersionCode",
    ),
}


def add_rollout_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-current-version",
        default=None,
        help="Optional maximum installed version eligible for this OTA release.",
    )
    parser.add_argument(
        "--channel",
        default="stable",
        choices=("dev", "alpha", "beta", "stable", "local"),
        help="OTA release channel. Default: stable.",
    )
    parser.add_argument(
        "--rollout-percentage",
        type=int,
        default=100,
        help="Deterministic rollout percentage, 0-100. Allowlisted hardware still receives the release.",
    )
    parser.add_argument(
        "--allow-hardware-device-id",
        action="append",
        default=[],
        help="Hardware device id allowed to receive this release regardless of rollout percentage. Repeatable.",
    )
    parser.add_argument("--rollback-release-id", default=None, help="Optional release id to use for rollback metadata.")
    parser.add_argument("--rollback-version", default=None, help="Optional rollback firmware version metadata.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and publish ESP32 OTA releases to local or GCP PlantLab backends.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish = subparsers.add_parser(
        "publish-local",
        help="Build or reuse firmware artifacts and publish them to the local Docker backend.",
    )
    publish.add_argument(
        "--node",
        choices=("master", "camera", "both"),
        required=True,
        help="Firmware target to publish.",
    )
    publish.add_argument("--version", required=True, help="Release version, for example 0.1.2.")
    publish.add_argument(
        "--version-code",
        type=int,
        default=None,
        help="Release version code. Defaults to the value in firmware_version.h for each node.",
    )
    publish.add_argument(
        "--min-current-version",
        default=None,
        help="Optional minimum installed version required for this OTA release.",
    )
    add_rollout_arguments(publish)
    publish.add_argument(
        "--release-suffix",
        default="local-test",
        help="Suffix for generated release IDs. Default: local-test.",
    )
    publish.add_argument(
        "--release-id",
        default=None,
        help="Explicit release ID. Only valid when --node is master or camera.",
    )
    publish.add_argument(
        "--artifact",
        type=Path,
        default=None,
        help="Use an existing firmware.bin instead of the PlatformIO build output. Only valid for one node.",
    )
    publish.add_argument("--build", action="store_true", help="Run PlatformIO build before publishing.")
    publish.add_argument(
        "--allow-version-mismatch",
        action="store_true",
        help="Allow publishing when --version or --version-code does not match firmware_version.h.",
    )

    publish_gcp = subparsers.add_parser(
        "publish-gcp",
        help="Build or reuse firmware artifacts, upload them to GCS, and publish releases through a Cloud Run job.",
    )
    publish_gcp.add_argument(
        "--node",
        choices=("master", "camera", "both"),
        required=True,
        help="Firmware target to publish.",
    )
    publish_gcp.add_argument("--version", required=True, help="Release version, for example 0.1.5.")
    publish_gcp.add_argument(
        "--version-code",
        type=int,
        default=None,
        help="Release version code. Defaults to the value in firmware_version.h for each node.",
    )
    publish_gcp.add_argument(
        "--min-current-version",
        default=None,
        help="Optional minimum installed version required for this OTA release.",
    )
    add_rollout_arguments(publish_gcp)
    publish_gcp.add_argument(
        "--release-suffix",
        default="gcp",
        help="Suffix for generated release IDs. Default: gcp.",
    )
    publish_gcp.add_argument(
        "--release-id",
        default=None,
        help="Explicit release ID. Only valid when --node is master or camera.",
    )
    publish_gcp.add_argument(
        "--artifact",
        type=Path,
        default=None,
        help="Use an existing firmware.bin instead of the PlatformIO build output. Only valid for one node.",
    )
    publish_gcp.add_argument("--build", action="store_true", help="Run PlatformIO build before publishing.")
    publish_gcp.add_argument(
        "--allow-version-mismatch",
        action="store_true",
        help="Allow publishing when --version or --version-code does not match firmware_version.h.",
    )
    publish_gcp.add_argument(
        "--project-id",
        default=env_default("PROJECT_ID", DEFAULT_PROJECT_ID),
        help="GCP project ID.",
    )
    publish_gcp.add_argument(
        "--region",
        default=env_default("REGION", DEFAULT_REGION),
        help="Cloud Run region.",
    )
    publish_gcp.add_argument(
        "--service-name",
        default=env_default("SERVICE_NAME", DEFAULT_SERVICE_NAME),
        help="Cloud Run backend service whose image should run the publish job.",
    )
    publish_gcp.add_argument(
        "--job-name",
        default=env_default("OTA_PUBLISH_JOB", DEFAULT_GCP_JOB_NAME),
        help="Cloud Run job used to upsert firmware release metadata.",
    )
    publish_gcp.add_argument(
        "--bucket-name",
        default=env_default("PLANTLAB_FIRMWARE_BUCKET_NAME", env_default("GCS_BUCKET_NAME", env_default("BUCKET_NAME", DEFAULT_BUCKET_NAME))),
        help="GCS bucket for firmware artifacts.",
    )
    publish_gcp.add_argument(
        "--firmware-prefix",
        default=env_default("PLANTLAB_FIRMWARE_PREFIX", DEFAULT_FIRMWARE_PREFIX),
        help="GCS object prefix for firmware artifacts.",
    )
    publish_gcp.add_argument(
        "--cloud-sql-connection-name",
        default=env_default("CLOUD_SQL_CONNECTION_NAME", DEFAULT_CLOUD_SQL_CONNECTION_NAME),
        help="Cloud SQL connection name used by the Cloud Run job.",
    )
    publish_gcp.add_argument(
        "--db-name",
        default=env_default("DB_NAME", DEFAULT_DB_NAME),
        help="Cloud SQL database name.",
    )
    publish_gcp.add_argument(
        "--db-user",
        default=env_default("DB_USER", DEFAULT_DB_USER),
        help="Cloud SQL database user.",
    )
    publish_gcp.add_argument(
        "--service-account",
        default=None,
        help="Cloud Run job service account. Defaults to plantlab-run-sa@<project-id>.iam.gserviceaccount.com.",
    )
    publish_gcp.add_argument(
        "--image",
        default=None,
        help="Backend container image for the Cloud Run job. Defaults to the current deployed service image.",
    )
    publish_gcp.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned GCS upload and Cloud Run job commands without changing GCP.",
    )

    bump = subparsers.add_parser(
        "bump-version",
        help="Update ESP32 firmware version constants before building an OTA release.",
    )
    bump.add_argument("--node", choices=("master", "camera", "both"), required=True)
    bump.add_argument("--version", required=True, help="New firmware version, for example 0.1.2.")
    bump.add_argument(
        "--version-code",
        type=int,
        default=None,
        help="New version code. Defaults to semantic version code, for example 0.1.2 -> 1002.",
    )

    subparsers.add_parser("status-local", help="Show local registered hardware OTA status.")
    releases = subparsers.add_parser("list-local-releases", help="Show recent local firmware releases.")
    releases.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()
    if args.command == "bump-version":
        return bump_version(args)
    if args.command == "publish-local":
        return publish_local(args)
    if args.command == "publish-gcp":
        return publish_gcp_release(args)
    if args.command == "status-local":
        return status_local()
    if args.command == "list-local-releases":
        return list_local_releases(args.limit)
    parser.error("unknown command")
    return 2


def publish_local(args: argparse.Namespace) -> int:
    selected = selected_targets(args.node)
    if args.release_id and len(selected) != 1:
        fail("--release-id can only be used with one node.")
    if args.artifact and len(selected) != 1:
        fail("--artifact can only be used with one node.")
    validate_rollout_args(args)

    require_file(FIRMWARE_VERSION_HEADER)
    ensure_local_docker_ready()

    for target in selected:
        declared = read_firmware_info(target)
        version_code = args.version_code if args.version_code is not None else declared.version_code
        if not args.allow_version_mismatch:
            if declared.version != args.version:
                fail(
                    f"{target.name} firmware declares version {declared.version}, "
                    f"but --version is {args.version}. "
                    f"Run: .venv/bin/python platform/infra/scripts/ota_release.py "
                    f"bump-version --node {args.node} --version {args.version}"
                )
            if declared.version_code != version_code:
                fail(
                    f"{target.name} firmware declares version code {declared.version_code}, "
                    f"but release version code is {version_code}."
                )

        firmware_path = args.artifact or target.firmware_path
        if args.build and args.artifact is None:
            build_firmware(target)
        require_file(firmware_path)

        release_id = args.release_id or generated_release_id(target, args.version, args.release_suffix)
        artifact_name = f"{release_id}.bin"
        artifact_path = CONTAINER_FIRMWARE_DIR + "/" + artifact_name
        artifact_size = firmware_path.stat().st_size
        checksum = sha256_file(firmware_path)

        print(f"[ota] publishing {target.name} release {release_id}")
        print(f"[ota] version={args.version} version_code={version_code}")
        print(f"[ota] channel={args.channel} rollout={args.rollout_percentage}%")
        print(f"[ota] artifact={firmware_path}")
        print(f"[ota] size={artifact_size} sha256={checksum}")

        docker_exec(PLATFORM_CONTAINER, "mkdir", "-p", CONTAINER_FIRMWARE_DIR)
        run(["docker", "cp", str(firmware_path), f"{PLATFORM_CONTAINER}:{artifact_path}"])
        upsert_release(
            release_id=release_id,
            target=target,
            version=args.version,
            version_code=version_code,
            min_current_version=args.min_current_version,
            max_current_version=args.max_current_version,
            channel=args.channel,
            rollout_percentage=args.rollout_percentage,
            allow_hardware_device_ids=args.allow_hardware_device_id,
            rollback_release_id=args.rollback_release_id,
            rollback_version=args.rollback_version,
            artifact_path=artifact_name,
            artifact_size=artifact_size,
            checksum=checksum,
        )
        print(f"[ota] release published: {release_id}")

    print("[ota] done. Devices will pick up the release on their next OTA manifest poll.")
    print("[ota] For immediate testing, reboot/reset devices that already checked OTA this boot.")
    print("[ota] Check progress with: .venv/bin/python platform/infra/scripts/ota_release.py status-local")
    return 0


def publish_gcp_release(args: argparse.Namespace) -> int:
    selected = selected_targets(args.node)
    if args.release_id and len(selected) != 1:
        fail("--release-id can only be used with one node.")
    if args.artifact and len(selected) != 1:
        fail("--artifact can only be used with one node.")
    validate_rollout_args(args)

    require_file(FIRMWARE_VERSION_HEADER)
    require_command_available("gcloud")

    project_id = args.project_id
    region = args.region
    service_name = args.service_name
    service_account = args.service_account or f"plantlab-run-sa@{project_id}.iam.gserviceaccount.com"
    backend_image = args.image or current_cloud_run_image(
        service_name=service_name,
        project_id=project_id,
        region=region,
    )
    if not backend_image:
        fail(
            "Could not determine backend image. Deploy the backend that contains "
            "app.ops.publish_firmware_release first, or pass --image."
        )

    for target in selected:
        declared = read_firmware_info(target)
        version_code = args.version_code if args.version_code is not None else declared.version_code
        if not args.allow_version_mismatch:
            validate_declared_version(target, declared, args.version, version_code, args.node)

        firmware_path = args.artifact or target.firmware_path
        if args.build and args.artifact is None:
            build_firmware(target)
        require_file(firmware_path)

        release_id = args.release_id or generated_release_id(target, args.version, args.release_suffix)
        artifact_name = f"{release_id}.bin"
        artifact_uri = gcs_artifact_uri(args.bucket_name, args.firmware_prefix, artifact_name)
        artifact_size = firmware_path.stat().st_size
        checksum = sha256_file(firmware_path)

        print(f"[ota] publishing GCP {target.name} release {release_id}")
        print(f"[ota] version={args.version} version_code={version_code}")
        print(f"[ota] channel={args.channel} rollout={args.rollout_percentage}%")
        print(f"[ota] artifact={firmware_path}")
        print(f"[ota] gcs={artifact_uri}")
        print(f"[ota] size={artifact_size} sha256={checksum}")

        upload_cmd = ["gcloud", "storage", "cp", str(firmware_path), artifact_uri]
        job_cmd = gcp_publish_job_command(
            job_name=args.job_name,
            image=backend_image,
            project_id=project_id,
            region=region,
            service_account=service_account,
            cloud_sql_connection_name=args.cloud_sql_connection_name,
            db_name=args.db_name,
            db_user=args.db_user,
            release_id=release_id,
            target=target,
            version=args.version,
            version_code=version_code,
            min_current_version=args.min_current_version,
            max_current_version=args.max_current_version,
            channel=args.channel,
            rollout_percentage=args.rollout_percentage,
            allow_hardware_device_ids=args.allow_hardware_device_id,
            rollback_release_id=args.rollback_release_id,
            rollback_version=args.rollback_version,
            artifact_path=artifact_uri,
            artifact_size=artifact_size,
            checksum=checksum,
        )
        execute_cmd = [
            "gcloud",
            "run",
            "jobs",
            "execute",
            args.job_name,
            "--project",
            project_id,
            "--region",
            region,
            "--wait",
        ]

        if args.dry_run:
            print("[ota] dry-run upload command:")
            print(shell_join(upload_cmd))
            print("[ota] dry-run Cloud Run job create/update command:")
            print(shell_join([part if part != "REPLACE_ACTION" else "create" for part in job_cmd]))
            print("[ota] dry-run Cloud Run job execute command:")
            print(shell_join(execute_cmd))
            continue

        run(upload_cmd)
        create_or_update_cloud_run_job(args.job_name, project_id, region, job_cmd)
        run(execute_cmd)
        print(f"[ota] GCP release published: {release_id}")

    if args.dry_run:
        print("[ota] dry-run complete. No GCP changes were made.")
    else:
        print("[ota] done. Production devices will pick up the release on their next OTA manifest poll.")
        print("[ota] For immediate testing, reboot/reset devices that already checked OTA this boot.")
    return 0


def bump_version(args: argparse.Namespace) -> int:
    require_file(FIRMWARE_VERSION_HEADER)
    selected = selected_targets(args.node)
    new_code = args.version_code if args.version_code is not None else semantic_version_code(args.version)
    if new_code <= 0:
        fail("Could not derive a positive version code. Pass --version-code explicitly.")

    versions = {name: read_firmware_info(target) for name, target in TARGETS.items()}
    for target in selected:
        versions[target.name] = FirmwareInfo(version=args.version, version_code=new_code)

    FIRMWARE_VERSION_HEADER.write_text(
        "\n".join(
            [
                "#pragma once",
                "",
                "namespace plantlab {",
                "",
                f'constexpr char kMasterSoftwareVersion[] = "{versions["master"].version}";',
                f"constexpr int kMasterSoftwareVersionCode = {versions['master'].version_code};",
                f'constexpr char kCameraSoftwareVersion[] = "{versions["camera"].version}";',
                f"constexpr int kCameraSoftwareVersionCode = {versions['camera'].version_code};",
                "",
                "}  // namespace plantlab",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"[ota] updated {FIRMWARE_VERSION_HEADER}")
    for target in selected:
        print(f"[ota] {target.name}: version={args.version} version_code={new_code}")
    return 0


def status_local() -> int:
    sql = """
select
  hardware_device_id,
  node_role,
  coalesce(hardware_model, '') as hardware_model,
  coalesce(software_version, '') as software_version,
  ota_status,
  coalesce(ota_target_version, '') as ota_target_version,
  coalesce(ota_release_id, '') as ota_release_id,
  coalesce(ota_progress::text, '') as ota_progress,
  coalesce(ota_error, '') as ota_error,
  coalesce(ota_last_success_at::text, '') as ota_last_success_at,
  coalesce(last_seen_at::text, '') as last_seen_at
from device_hardware_ids
order by node_role desc, hardware_device_id;
""".strip()
    print(run_psql(sql))
    return 0


def list_local_releases(limit: int) -> int:
    safe_limit = max(1, min(limit, 100))
    sql = f"""
select
  release_id,
  node_role,
  coalesce(hardware_model, '') as hardware_model,
  version,
  version_code,
  channel,
  rollout_percentage,
  coalesce(rollback_version, '') as rollback_version,
  status,
  artifact_path,
  artifact_size_bytes,
  coalesce(published_at::text, '') as published_at
from firmware_releases
order by created_at desc
limit {safe_limit};
""".strip()
    print(run_psql(sql))
    return 0


def build_firmware(target: OtaTarget) -> None:
    require_file(PIO_BIN)
    env = {"PLATFORMIO_CORE_DIR": str(PIO_CORE_DIR)}
    print(f"[ota] building PlatformIO env {target.pio_env}")
    run([str(PIO_BIN), "run", "-e", target.pio_env], cwd=ESP32_DIR, env=env)


def validate_declared_version(
    target: OtaTarget,
    declared: FirmwareInfo,
    version: str,
    version_code: int,
    node_arg: str,
) -> None:
    if declared.version != version:
        fail(
            f"{target.name} firmware declares version {declared.version}, "
            f"but --version is {version}. "
            f"Run: .venv/bin/python platform/infra/scripts/ota_release.py "
            f"bump-version --node {node_arg} --version {version}"
        )
    if declared.version_code != version_code:
        fail(
            f"{target.name} firmware declares version code {declared.version_code}, "
            f"but release version code is {version_code}."
        )


def validate_rollout_args(args: argparse.Namespace) -> None:
    if args.max_current_version and len(args.max_current_version) > 120:
        fail("--max-current-version must be 120 characters or fewer.")
    if args.rollout_percentage < 0 or args.rollout_percentage > 100:
        fail("--rollout-percentage must be between 0 and 100.")
    for hardware_device_id in args.allow_hardware_device_id:
        if not str(hardware_device_id).strip():
            fail("--allow-hardware-device-id must not be empty.")
        if len(hardware_device_id) > 120:
            fail("--allow-hardware-device-id values must be 120 characters or fewer.")
    if args.rollback_release_id and len(args.rollback_release_id) > 80:
        fail("--rollback-release-id must be 80 characters or fewer.")
    if args.rollback_version and len(args.rollback_version) > 120:
        fail("--rollback-version must be 120 characters or fewer.")


def current_cloud_run_image(*, service_name: str, project_id: str, region: str) -> str:
    return run(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            service_name,
            "--project",
            project_id,
            "--region",
            region,
            "--format=value(spec.template.spec.containers[0].image)",
        ],
        capture=True,
    ).strip()


def gcs_artifact_uri(bucket_name: str, prefix: str, artifact_name: str) -> str:
    bucket = bucket_name.strip().removeprefix("gs://").strip("/")
    if not bucket:
        fail("GCS bucket name is empty.")
    clean_prefix = prefix.strip().strip("/")
    clean_artifact = artifact_name.strip().lstrip("/")
    if not clean_artifact:
        fail("Firmware artifact name is empty.")
    if clean_prefix:
        return f"gs://{bucket}/{clean_prefix}/{clean_artifact}"
    return f"gs://{bucket}/{clean_artifact}"


def gcp_publish_job_command(
    *,
    job_name: str,
    image: str,
    project_id: str,
    region: str,
    service_account: str,
    cloud_sql_connection_name: str,
    db_name: str,
    db_user: str,
    release_id: str,
    target: OtaTarget,
    version: str,
    version_code: int,
    min_current_version: str | None,
    max_current_version: str | None,
    channel: str,
    rollout_percentage: int,
    allow_hardware_device_ids: list[str],
    rollback_release_id: str | None,
    rollback_version: str | None,
    artifact_path: str,
    artifact_size: int,
    checksum: str,
) -> list[str]:
    args = [
        "-m",
        "app.ops.publish_firmware_release",
        "--release-id",
        release_id,
        "--node-role",
        target.node_role,
        "--hardware-model",
        target.hardware_model,
        "--version",
        version,
        "--version-code",
        str(version_code),
        "--artifact-path",
        artifact_path,
        "--artifact-size-bytes",
        str(artifact_size),
        "--sha256",
        checksum,
    ]
    if min_current_version:
        args.extend(["--min-current-version", min_current_version])
    if max_current_version:
        args.extend(["--max-current-version", max_current_version])
    args.extend(["--channel", channel])
    args.extend(["--rollout-percentage", str(rollout_percentage)])
    for hardware_device_id in allow_hardware_device_ids:
        args.extend(["--allow-hardware-device-id", hardware_device_id])
    if rollback_release_id:
        args.extend(["--rollback-release-id", rollback_release_id])
    if rollback_version:
        args.extend(["--rollback-version", rollback_version])

    return [
        "gcloud",
        "run",
        "jobs",
        "REPLACE_ACTION",
        job_name,
        "--image",
        image,
        "--project",
        project_id,
        "--region",
        region,
        "--service-account",
        service_account,
        "--set-cloudsql-instances",
        cloud_sql_connection_name,
        "--tasks",
        "1",
        "--max-retries",
        "0",
        "--command=python",
        f"--args={','.join(args)}",
        "--set-env-vars="
        + gcp_publish_env_vars(db_name=db_name, db_user=db_user, cloud_sql_connection_name=cloud_sql_connection_name),
        "--set-secrets=APP_SECRET_KEY=app-secret-key:latest,DB_PASSWORD=db-password:latest,PLANTLAB_PROVISIONING_SHARED_SECRET=provisioning-shared-secret:latest",
    ]


def gcp_publish_env_vars(*, db_name: str, db_user: str, cloud_sql_connection_name: str) -> str:
    return (
        "^~^APP_ENV=production"
        f"~DB_NAME={db_name}"
        f"~DB_USER={db_user}"
        f"~CLOUD_SQL_CONNECTION_NAME={cloud_sql_connection_name}"
        "~PLANTLAB_DEV_TOKEN_AUTH_ENABLED=false"
    )


def create_or_update_cloud_run_job(job_name: str, project_id: str, region: str, command: list[str]) -> None:
    if command_succeeds(["gcloud", "run", "jobs", "describe", job_name, "--project", project_id, "--region", region]):
        action = "update"
    else:
        action = "create"
    job_command = [part if part != "REPLACE_ACTION" else action for part in command]
    print(f"[ota] {action} Cloud Run job {job_name}")
    run(job_command)


def upsert_release(
    *,
    release_id: str,
    target: OtaTarget,
    version: str,
    version_code: int,
    min_current_version: str | None,
    max_current_version: str | None,
    channel: str,
    rollout_percentage: int,
    allow_hardware_device_ids: list[str],
    rollback_release_id: str | None,
    rollback_version: str | None,
    artifact_path: str,
    artifact_size: int,
    checksum: str,
) -> None:
    allowed_hardware = json.dumps(sorted(set(allow_hardware_device_ids))) if allow_hardware_device_ids else None
    sql = f"""
insert into firmware_releases (
  release_id,
  node_role,
  hardware_model,
  version,
  version_code,
  min_current_version,
  max_current_version,
  channel,
  rollout_percentage,
  allowed_hardware_device_ids,
  rollback_release_id,
  rollback_version,
  artifact_path,
  artifact_size_bytes,
  sha256,
  signature,
  status,
  created_at,
  published_at
) values (
  {sql_literal(release_id)},
  {sql_literal(target.node_role)},
  {sql_literal(target.hardware_model)},
  {sql_literal(version)},
  {version_code},
  {sql_literal(min_current_version)},
  {sql_literal(max_current_version)},
  {sql_literal(channel)},
  {rollout_percentage},
  {sql_literal(allowed_hardware)},
  {sql_literal(rollback_release_id)},
  {sql_literal(rollback_version)},
  {sql_literal(artifact_path)},
  {artifact_size},
  {sql_literal(checksum)},
  null,
  'published',
  now(),
  now()
)
on conflict (release_id) do update set
  node_role = excluded.node_role,
  hardware_model = excluded.hardware_model,
  version = excluded.version,
  version_code = excluded.version_code,
  min_current_version = excluded.min_current_version,
  max_current_version = excluded.max_current_version,
  channel = excluded.channel,
  rollout_percentage = excluded.rollout_percentage,
  allowed_hardware_device_ids = excluded.allowed_hardware_device_ids,
  rollback_release_id = excluded.rollback_release_id,
  rollback_version = excluded.rollback_version,
  artifact_path = excluded.artifact_path,
  artifact_size_bytes = excluded.artifact_size_bytes,
  sha256 = excluded.sha256,
  signature = excluded.signature,
  status = excluded.status,
  published_at = now();
""".strip()
    run_psql(sql, print_output=True)


def read_firmware_info(target: OtaTarget) -> FirmwareInfo:
    text = FIRMWARE_VERSION_HEADER.read_text(encoding="utf-8")
    version_match = re.search(
        rf"{re.escape(target.version_symbol)}\[\]\s*=\s*\"([^\"]+)\"",
        text,
    )
    code_match = re.search(
        rf"{re.escape(target.version_code_symbol)}\s*=\s*(\d+)",
        text,
    )
    if not version_match or not code_match:
        fail(f"Could not read {target.name} version constants from {FIRMWARE_VERSION_HEADER}.")
    return FirmwareInfo(version=version_match.group(1), version_code=int(code_match.group(1)))


def selected_targets(node: str) -> list[OtaTarget]:
    return list(TARGETS.values()) if node == "both" else [TARGETS[node]]


def semantic_version_code(version: str) -> int:
    match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?.*", version.strip())
    if not match:
        return 0
    major = int(match.group(1) or 0)
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    return major * 1_000_000 + minor * 1_000 + patch


def ensure_local_docker_ready() -> None:
    names = run(["docker", "ps", "--format", "{{.Names}}"], capture=True).splitlines()
    missing = [name for name in (PLATFORM_CONTAINER, POSTGRES_CONTAINER) if name not in names]
    if missing:
        fail(
            "Required local Docker container(s) are not running: "
            + ", ".join(missing)
            + "\nStart them with: docker compose -f platform/infra/docker/docker-compose.local.yml up -d --build"
        )


def run_psql(sql: str, *, print_output: bool = False) -> str:
    output = run(
        [
            "docker",
            "exec",
            "-i",
            POSTGRES_CONTAINER,
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-v",
            "ON_ERROR_STOP=1",
            "-P",
            "pager=off",
            "-c",
            sql,
        ],
        capture=not print_output,
    )
    return output


def docker_exec(container: str, *args: str) -> None:
    run(["docker", "exec", container, *args])


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> str:
    process_env = None
    if env:
        import os

        process_env = os.environ.copy()
        process_env.update(env)

    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            env=process_env,
            text=True,
            check=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
        )
    except FileNotFoundError as exc:
        fail(f"Command not found: {cmd[0]}")
        raise exc
    except subprocess.CalledProcessError as exc:
        if capture and exc.stdout:
            print(exc.stdout, end="")
        fail(f"Command failed: {' '.join(cmd)}")
        raise exc
    return completed.stdout.strip() if capture and completed.stdout else ""


def command_succeeds(cmd: list[str]) -> bool:
    completed = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return completed.returncode == 0


def require_command_available(command: str) -> None:
    if shutil.which(command) is None:
        fail(f"Command not found: {command}")


def shell_join(cmd: list[str]) -> str:
    return shlex.join(cmd)


def env_default(name: str, fallback: str) -> str:
    value = os.getenv(name)
    if value is not None and value.strip():
        return value.strip()
    env_values = read_infra_env_file()
    return env_values.get(name, fallback)


def read_infra_env_file() -> dict[str, str]:
    if not INFRA_ENV_FILE.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in INFRA_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = raw_value.strip()
        try:
            parsed = shlex.split(value, comments=False, posix=True)
        except ValueError:
            parsed = []
        values[key] = parsed[0] if len(parsed) == 1 else value.strip("\"'")
    return values


def generated_release_id(target: OtaTarget, version: str, suffix: str) -> str:
    raw = f"{target.name}-{version}-{suffix}"
    release_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-").lower()
    if not release_id:
        fail("Generated empty release ID.")
    if len(release_id) > 80:
        fail(f"Generated release ID is too long: {release_id}")
    return release_id


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sql_literal(value: str | None) -> str:
    if value is None:
        return "null"
    return "'" + value.replace("'", "''") + "'"


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"Required file not found: {path}")


def fail(message: str) -> None:
    print(f"[ota] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    raise SystemExit(main())
