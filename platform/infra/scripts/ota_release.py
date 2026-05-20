#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
ESP32_DIR = ROOT_DIR / "device" / "esp32"
FIRMWARE_VERSION_HEADER = ESP32_DIR / "include" / "firmware_version.h"
PIO_BIN = ROOT_DIR / ".venv" / "bin" / "pio"
PIO_CORE_DIR = ROOT_DIR / ".pio-core"

PLATFORM_CONTAINER = "plantlab-local-platform"
POSTGRES_CONTAINER = "plantlab-local-postgres"
POSTGRES_USER = "plantlab_user"
POSTGRES_DB = "plantlab"
CONTAINER_FIRMWARE_DIR = "/app/platform/backend/data/firmware"


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and publish ESP32 OTA releases to the local PlantLab backend.",
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
            artifact_path=artifact_name,
            artifact_size=artifact_size,
            checksum=checksum,
        )
        print(f"[ota] release published: {release_id}")

    print("[ota] done. Devices will pick up the release on their next OTA manifest poll.")
    print("[ota] For immediate testing, reboot/reset devices that already checked OTA this boot.")
    print("[ota] Check progress with: .venv/bin/python platform/infra/scripts/ota_release.py status-local")
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


def upsert_release(
    *,
    release_id: str,
    target: OtaTarget,
    version: str,
    version_code: int,
    min_current_version: str | None,
    artifact_path: str,
    artifact_size: int,
    checksum: str,
) -> None:
    sql = f"""
insert into firmware_releases (
  release_id,
  node_role,
  hardware_model,
  version,
  version_code,
  min_current_version,
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
