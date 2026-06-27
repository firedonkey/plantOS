# Current State

Last updated: 2026-06-26.

Read this file first when moving PlantLab to a new computer or starting a new
Codex session. It records verified facts from the repository at migration-prep
time; uncertain items are marked as Needs verification.

## Repository

- Repository root on the current machine: `/Users/gary/plantOS`
- Branch: `main`
- Remote: `origin git@github.com:firedonkey/plantOS.git`
- Checked local commit before migration-prep docs/scripts: `1e0757d`
- Checked `origin/main` before migration-prep docs/scripts: `1e0757d`
- Current migration-prep changes are docs, ignore rules, and utility scripts.
- Root `data/` currently contains local runtime artifacts and is not intended
  for Git.

Needs verification after cloning:

- Whether `main` still points to the intended latest commit.
- Whether local-only runtime data was backed up or intentionally discarded.

## Project Purpose

PlantLab is an end-to-end plant monitoring system with ESP32 firmware, a backend
API, web and mobile apps, provisioning services, demo account support, GCP
deployment tooling, and a local simulator.

## Product Components

- ESP32 master and XIAO ESP32S3 camera firmware: `device/esp32/`
- FastAPI backend: `platform/backend/`
- React/Vite web app: `platform/web/`
- Expo React Native mobile app: `platform/mobile/`
- Node/Express provisioning API: `provision_backend/`
- Shared protocol contracts: `contracts/`
- Local/GCP infra helpers: `platform/infra/`
- Local simulator: `tools/simulator/`

## Current Working State

- Demo account and public demo web changes are committed and were deployed to
  GCP in a prior workflow.
- OV5640 autofocus camera work is committed as WIP in `1e0757d`; the user stated
  it is not fully functional and needs improvement.
- The firmware flash helper is portable and defaults to `--dry-run`; hardware
  upload requires explicit `--flash`.
- `scripts/setup_new_machine.sh --check` is intended to inspect local tooling
  without installing dependencies.
- Node major `22` is pinned in `.nvmrc` and package `engines` fields.
- `scripts/validate_repo.sh --docs` is intended to run static validation only.

## Hardware Configuration

Verified from firmware code/docs:

- Master board target: `ESP32-S3-DevKitC-1-N32R16V`.
- Camera board target: Seeed Studio XIAO ESP32S3 Sense.
- Master firmware version: `0.1.6`.
- Camera firmware version: `0.1.8`.
- Camera wrapper recognizes OV2640, OV3660, and OV5640 sensor IDs.
- `PLANTLAB_OV5640_AF_ENABLED` is used for OV5640 autofocus support in camera
  test/platform environments.

Needs verification:

- Physical wiring, PCB revision, and sensor calibration on the bench.
- Water sensor wiring and touch thresholds.
- OV3660 image quality after reverting to the old camera.
- OV5640/DC5640-AF autofocus and image quality before production use.

## Software Architecture

Runtime flow:

1. Web/mobile clients call the FastAPI backend for auth, devices, readings,
   commands, images, diagnostics, firmware, setup, and demo data.
2. The provisioning backend manages setup-code, claim-token, and hardware
   registration flows.
3. The ESP32 master sends readings/heartbeats and polls backend commands.
4. The master forwards camera capture requests to the camera node over ESP-NOW.
5. The camera node uploads JPEG images and reports camera health.
6. Backend APIs expose dashboard, image history, diagnostics, command, and OTA
   state.

## Deployment And Development Status

- Backend Cloud Run helper exists at `platform/infra/cloud-run/deploy_backend.sh`.
- Provisioning Cloud Run helper exists at
  `platform/infra/cloud-run/deploy_provisioning_backend.sh`.
- Web Cloud Build config exists at `platform/infra/docker/cloudbuild.web.yaml`.
- No dedicated web deployment helper equivalent to the backend helpers was found.

Needs verification:

- Current GCP project, IAM, Secret Manager values, Cloud SQL access, and Cloud
  Run service state on the new machine.
- Whether web deployment should get a dedicated, verified helper script.
- Exact npm patch version for repeatable web/mobile/provisioning workflows.

## Safety Constraints

- Do not commit secrets or real `.env` values.
- Do not flash hardware unless explicitly requested and the serial port is
  verified.
- Do not change pin mappings, OTA behavior, provisioning behavior, database
  migrations, deployment traffic, or production data during migration prep.
- Treat root `data/`, local DB files, uploads, `.venv/`, `node_modules/`,
  `.pio-core/`, and `device/esp32/.pio/` as local-only.

## Safe Validation Commands

Static validation only:

```bash
scripts/validate_repo.sh --docs
scripts/setup_new_machine.sh --check
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --dry-run
```

Full local validation, when dependencies are installed:

```bash
scripts/validate_repo.sh --all
```

## Next Prioritized Tasks

1. Back up or intentionally discard local-only runtime data before migration.
2. Clone on the new computer and run `scripts/setup_new_machine.sh --check`.
3. Create local env files from examples and fill secrets from a secure source.
4. Run `scripts/setup_new_machine.sh --python --node`.
5. Run `scripts/validate_repo.sh --all`.
6. Bench-test serial ports and firmware build/flash commands.
7. Verify GCP deployment access and document or add a web deployment helper only
   after the exact workflow is confirmed.
8. Continue OV5640 autofocus/image-quality work in a separate functional task.
