# Project Brief

PlantOS is a local-to-cloud plant monitoring and control system. It includes ESP32 firmware for the master node and camera node, backend services, a mobile app, a web app, and deployment tooling.

## Primary Users

- PlantLab device owner using the iOS app.
- Developer/operator maintaining firmware, backend, mobile, web, and GCP deployment.
- Future Pantheon agents working inside this repository.

## Main Features

- BLE Wi-Fi provisioning and repair flows.
- ESP32 master node sensor reporting and grow LED control.
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
