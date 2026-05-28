# PlantLab

PlantLab is a smart indoor plant monitoring system by Mars Potato Lab. This
repository contains the ESP32 firmware, FastAPI backend, React web app, Expo
mobile app, provisioning backend, simulator, contracts, and deployment tooling.

## Current Architecture

- ESP32-S3 master node for sensors, grow-light state, heartbeat, diagnostics,
  command polling, and OTA flow.
- ESP32-S3 camera node for image capture and upload.
- FastAPI backend for devices, auth, readings, images, commands, OTA,
  diagnostics, canonical events, and timeline APIs.
- Vite React web app for the public landing page, demo, dashboard, images, and
  diagnostics timeline.
- Expo React Native mobile app for provisioning and mobile dashboard usage.
- Node provisioning backend for setup claim/token flows.
- Contract-first JSON protocol shared across firmware, backend, web, mobile,
  and simulator.

The legacy Raspberry Pi device runtime has been removed. Current device work
lives under `device/esp32/`.

## Repository Structure

```text
plantOS/
  contracts/              shared JSON Schemas and generated contract outputs
  device/
    esp32/                ESP32-S3 master/camera firmware and tests
  docs/                   architecture, protocol, validation, and design docs
  platform/
    backend/              FastAPI backend, migrations, and tests
    web/                  Vite React web app
    mobile/               Expo React Native app
    infra/                Docker, Cloud Run, env, and operations scripts
  provision_backend/      Node provisioning backend
  tools/
    simulator/            local protocol simulator
```

For the current design source of truth, start with:

- [Design Docs Index](/Users/gary/plantOS/docs/design/README.md)
- [Current System Design](/Users/gary/plantOS/docs/design/current_system_design.md)
- [Device Protocol](/Users/gary/plantOS/docs/device_protocol.md)
- [Simulator Guide](/Users/gary/plantOS/docs/simulator.md)

## Local Development

Start the local Docker stack:

```bash
docker compose -f platform/infra/docker/docker-compose.local.yml up --build
```

Common local URLs:

- Web app: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Admin web: `http://localhost:5174`
- Provisioning backend: `http://localhost:3000`

Run backend tests:

```bash
.venv/bin/pytest platform/backend/tests -q
```

Run web validation:

```bash
npm --prefix platform/web run typecheck
npm --prefix platform/web run build
```

Run mobile validation:

```bash
npm --prefix platform/mobile run typecheck
```

Build ESP32 firmware:

```bash
.venv/bin/pio run -d device/esp32 -e esp32-local
.venv/bin/pio run -d device/esp32 -e camera-platform-test
```

Run simulator smoke tests:

```bash
.venv/bin/pytest tools/simulator/test_simulator_smoke.py -q
python3 -m compileall -q tools/simulator
```

## Simulator

The simulator uses real backend APIs and contract envelopes. It can generate
heartbeats, diagnostics, command results, OTA status, image events, and timeline
activity without physical hardware.

Example:

```bash
python3 tools/simulator/simulator.py \
  --base-url http://localhost:8000 \
  --device-id 1 \
  --device-token REAL_API_TOKEN_FROM_DB \
  --devices 1 \
  --camera-nodes 1 \
  --scenario unstable_wifi
```

See [docs/simulator.md](/Users/gary/plantOS/docs/simulator.md).

## Firmware

ESP32 firmware is in [device/esp32](/Users/gary/plantOS/device/esp32).

Useful commands:

```bash
cd device/esp32
../../.venv/bin/pio run -e esp32-local
../../.venv/bin/pio run -e camera-platform-test
```

## Public Web

The public marketing homepage lives at `/`.

The no-auth product demo lives at `/demo` and uses static web-owned demo assets
under `platform/web/src/assets/demo`.

The root route must remain a landing page for both signed-in and signed-out
users. Auth state should only change CTA labels or destinations.

## Validation

Before committing product or protocol changes, run the smallest relevant
validation set and include the results in the commit/report. Typical checks:

```bash
npm --prefix platform/web run typecheck
npm --prefix platform/web run build
npm --prefix platform/mobile run typecheck
.venv/bin/pytest platform/backend/tests -q
.venv/bin/pytest tools/simulator/test_simulator_smoke.py -q
git diff --check
```

Firmware changes should also run the relevant PlatformIO builds.
