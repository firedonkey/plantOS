# Architecture

This document summarizes verified repository structure and runtime components. For deeper design notes, also read `docs/design/current_system_design.md`, `docs/device_protocol.md`, and `docs/simulator.md`.

## Components

PlantLab is organized around these components:

- ESP32-S3 master firmware in `device/esp32/`.
- XIAO ESP32S3 camera-node firmware in `device/esp32/`.
- FastAPI backend in `platform/backend/`.
- Vite React web app in `platform/web/`.
- Expo React Native mobile app in `platform/mobile/`.
- Node/Express provisioning backend in `provision_backend/`.
- Shared device contracts in `contracts/`.
- Docker, Cloud Run, and operations tooling in `platform/infra/`.
- Local simulator in `tools/simulator/`.

## Runtime Flow

Verified from existing docs and code:

1. Mobile/web clients talk to the FastAPI backend for auth, devices, readings, commands, images, diagnostics, firmware, and setup flows.
2. The provisioning backend handles setup-code, claim-token, and hardware registration flows used during onboarding.
3. ESP32 master firmware sends readings and heartbeats to hardware APIs and polls for commands.
4. The master forwards camera capture work to the camera node over ESP-NOW.
5. The camera node captures JPEG images, uploads them to the backend, and reports health/status.
6. Backend APIs expose dashboard state, image history, diagnostics timeline, command state, and OTA metadata to web/mobile clients.

## Backend

- Framework: FastAPI.
- Entrypoint: `platform/backend/app/main.py`.
- Local app package: `platform/backend/app/`.
- Tests: `platform/backend/tests/`.
- Migrations: `platform/backend/migrations/versions/`.
- Migration runner: Alembic config at `platform/backend/alembic.ini`.
- Dependencies: `platform/backend/requirements.txt`.

Useful commands:

```bash
.venv/bin/pytest platform/backend/tests -q

cd platform/backend
../../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
../../.venv/bin/alembic upgrade head
```

## Web

- Framework: React/Vite.
- Source: `platform/web/src/`.
- Package scripts are in `platform/web/package.json`.
- Public landing page route: `/`.
- Public demo route: `/demo`.

Useful commands:

```bash
npm --prefix platform/web run dev
node --test platform/web/test/*.test.js
npm --prefix platform/web run typecheck
npm --prefix platform/web run build
npm --prefix platform/web run preview
```

## Mobile

- Framework: Expo React Native.
- Source: `platform/mobile/src/`.
- Package scripts are in `platform/mobile/package.json`.
- EAS config: `platform/mobile/eas.json`.

Useful commands:

```bash
npm --prefix platform/mobile run start
npm --prefix platform/mobile run start:dev:local -- --host lan
npm --prefix platform/mobile run typecheck
npm --prefix platform/mobile run test:unit
npm --prefix platform/mobile run build:ios:local -- --check-only
```

## Provisioning Backend

- Framework/runtime: Node.
- Source: `provision_backend/src/`.
- Package scripts are in `provision_backend/package.json`.
- Dockerfile: `provision_backend/Dockerfile`.

Useful commands:

```bash
npm --prefix provision_backend test
npm --prefix provision_backend run dev
```

## Firmware

- PlatformIO project: `device/esp32/`.
- Environments are defined in `device/esp32/platformio.ini`.
- Flash helper: `device/esp32/scripts/flash_esp32.sh`.

Useful commands:

```bash
.venv/bin/pio run -d device/esp32 -e esp32-local
.venv/bin/pio run -d device/esp32 -e esp32-gcp
.venv/bin/pio run -d device/esp32 -e camera-platform-test
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --dry-run
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --build-only
./device/esp32/scripts/flash_esp32.sh --local --port /dev/cu.usbmodem11401 --flash
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem12201 --flash --monitor
```

The flash helper resolves paths from its own location and defaults to a dry run.
Hardware upload requires explicit `--flash`.

## Local Docker Stack

Compose file: `platform/infra/docker/docker-compose.local.yml`.

Services:

- `postgres` on host port `5432`.
- `platform` backend on host port `8000`.
- `web` on host port `5173`.
- `admin-web` on host port `5174`.
- `provision-backend` on host port `3000`.

Command:

```bash
docker compose -f platform/infra/docker/docker-compose.local.yml up --build
```

## GCP Deployment

Backend deploy helper:

```bash
platform/infra/cloud-run/deploy_backend.sh print-config
platform/infra/cloud-run/deploy_backend.sh preflight
platform/infra/cloud-run/deploy_backend.sh test-local
platform/infra/cloud-run/deploy_backend.sh build
platform/infra/cloud-run/deploy_backend.sh backup
platform/infra/cloud-run/deploy_backend.sh migrate
platform/infra/cloud-run/deploy_backend.sh deploy-candidate
VERIFY_URL="<candidate-url>" platform/infra/cloud-run/deploy_backend.sh verify-health
CONFIRM_SHIFT_TRAFFIC=yes platform/infra/cloud-run/deploy_backend.sh shift-traffic
```

Provisioning deploy helper:

```bash
platform/infra/cloud-run/deploy_provisioning_backend.sh print-config
platform/infra/cloud-run/deploy_provisioning_backend.sh preflight
platform/infra/cloud-run/deploy_provisioning_backend.sh test-local
platform/infra/cloud-run/deploy_provisioning_backend.sh build
platform/infra/cloud-run/deploy_provisioning_backend.sh deploy-candidate
VERIFY_URL="<candidate-url>" platform/infra/cloud-run/deploy_provisioning_backend.sh verify-health
CONFIRM_SHIFT_TRAFFIC=yes platform/infra/cloud-run/deploy_provisioning_backend.sh shift-traffic
```

Needs verification: the repo has a web Cloud Build config at `platform/infra/docker/cloudbuild.web.yaml`, but there is no dedicated web deployment helper script equivalent to the backend helpers.
