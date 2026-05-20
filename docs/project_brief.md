# Project Brief

PlantOS is a local-to-cloud plant monitoring and control system. It includes ESP32 firmware for the master node and camera node, backend services, a mobile app, a web app, and deployment tooling.

## Primary Users

- PlantLab device owner using the iOS app.
- Developer/operator maintaining firmware, backend, mobile, web, and GCP deployment.
- Future Pantheon agents working inside this repository.

## Main Features

- BLE Wi-Fi provisioning and repair flows.
- ESP32 master node sensor reporting and grow LED on/off or capability-gated intensity control.
- ESP-NOW camera node scheduling and manual capture.
- Backend APIs for auth, devices, readings, images, firmware OTA, and diagnostics.
- Mobile and web dashboards for device status, recent images, trends, and settings.
- Local Docker and Cloud Run deployment scripts.

## Main Modules

- `device/esp32/`: ESP32 master and camera firmware.
- `device/raspberry_pi/`: older Raspberry Pi provisioning experiments and hardware tests.
- `platform/backend/`: FastAPI backend, SQLAlchemy models, Alembic migrations, and tests.
- `platform/mobile/`: Expo React Native mobile app.
- `platform/web/`: Vite React web app.
- `platform/infra/`: Docker, Cloud Run, env, and diagnostic scripts.
- `provision_backend/`: provisioning backend service.
- `.pantheon/`: local Pantheon project control state.

## How To Run It

- Start local platform with Docker from `platform/infra/docker/`.
- Run backend tests from `platform/backend/`.
- Run mobile commands from `platform/mobile/`.
- Flash ESP32 with `./scripts/flash_esp32.sh` from `device/esp32/`.

## Current Risks / Unfinished Areas

- Raspberry Pi hardware tests require board-specific dependencies and should not be collected by generic macOS `pytest .` runs.
- Device release/list cleanup remains tracked as a TODO task.
- Cloud deployment should use the scripts under `platform/infra/cloud-run/`.

<!-- pantheon-memory:20260519T235300Z:20260519_235300_fix_plantos_sensor_trends_the_wa:docs/project_brief.md -->
## Project Brief Note: 2026-05-20T00:09:43.980964+00:00 - 20260519_235300_fix_plantos_sensor_trends_the_wa

- Run: `20260519T235300Z`
- Task: Fix PlantOS sensor trends: the water temperature chart currently shows no dat...
- Summary: Reviewer approved the implementation.
- Reason this file was listed: task memory_updates_expected included `docs/project_brief.md`.
- Review source: `/Users/gary/pantheon/runs/20260519T235300Z`
- Human review note: keep this append-only note if it remains accurate; refine surrounding context only after review.

<!-- pantheon-memory:20260520T055255Z:20260520_055255_create_a_support_admin_diagnosti:docs/project_brief.md -->
## Project Brief Note: 2026-05-20T06:27:55.670842+00:00 - 20260520_055255_create_a_support_admin_diagnosti

- Run: `20260520T055255Z`
- Task: Create a support/admin diagnostics panel so I can quickly understand device/u...
- Summary: Reviewer approved the implementation.
- Reason this file was listed: task memory_updates_expected included `docs/project_brief.md`.
- Review source: `/Users/gary/pantheon/runs/20260520T055255Z`
- Human review note: keep this append-only note if it remains accurate; refine surrounding context only after review.
