# Architecture Context

## Project Structure

- Firmware lives in `device/esp32/` and is built with PlatformIO.
- Backend application code lives in `platform/backend/app/` with tests under `platform/backend/tests/`.
- Mobile app code lives in `platform/mobile/` and uses Expo/EAS.
- Web app code lives in `platform/web/` and uses Vite.
- Deployment and local operations live in `platform/infra/`.
- Provisioning backend code lives in `provision_backend/`.
- Pantheon project state lives in `.pantheon/`; legacy `agent-workspace/` has been removed.

## Main Components

- ESP32 master firmware handles sensors, BLE provisioning, Wi-Fi validation, runtime registration, heartbeat, OTA metadata, and camera scheduling.
- ESP32 camera firmware receives ESP-NOW commands, captures images, uploads to the backend, and reports node health.
- FastAPI backend owns device, reading, image, command, firmware, diagnostics, and auth APIs.
- Expo mobile app is the primary user interface for onboarding and dashboard usage.
- Vite web app is the standalone browser UI.
- Provisioning backend issues and resolves setup claims for device onboarding.

## Data Flow

1. Mobile app provisions ESP32 over BLE with Wi-Fi and backend URLs.
2. ESP32 validates Wi-Fi locally, stores pending config, reboots, and registers with the backend.
3. Master node uploads heartbeat/readings and forwards camera commands over ESP-NOW.
4. Camera node uploads images to the backend.
5. Mobile/web clients poll backend APIs for dashboard state.

## Config / Environment Variables

- Local and deployment env files live under `platform/infra/env/`.
- Mobile and web have their own `.env.example` files.
- Secrets must not be committed.

## Test Strategy

- Backend: run focused pytest from `platform/backend/`.
- Mobile/web: run package scripts from their package roots.
- ESP32: run PlatformIO builds/tests from `device/esp32/`.

## Known Risks

- BLE/ESP-NOW/Wi-Fi coexistence must be validated on hardware.
- Production Cloud Run deploys require correct Secret Manager and env configuration.
- Camera upload latency depends on TLS and Cloud Run response behavior.
