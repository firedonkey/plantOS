# Project Map

## Important Folders

- `.pantheon/`: Pantheon target-project control state.
- `device/esp32/`: ESP32 firmware, PlatformIO config, firmware tests, and flash scripts.
- `device/raspberry_pi/`: Raspberry Pi hardware scripts/tests; requires Pi-specific dependencies.
- `docs/`: repo documentation and Pantheon target context.
- `platform/backend/`: FastAPI backend app, migrations, and tests.
- `platform/mobile/`: Expo React Native mobile app.
- `platform/web/`: Vite React web app.
- `platform/infra/`: Docker, Cloud Run, env docs, and operational scripts.
- `platform/shared/`: OpenAPI and shared contract docs.
- `provision_backend/`: Node provisioning backend.

## Important Files

- `README.md`: repo overview and local workflow.
- `device/esp32/platformio.ini`: ESP32 build environments.
- `platform/backend/requirements.txt`: backend Python dependencies.
- `platform/mobile/package.json`: mobile scripts.
- `platform/web/package.json`: web scripts.
- `platform/infra/cloud-run/deploy_backend.sh`: backend Cloud Run deployment.
- `platform/infra/cloud-run/deploy_provisioning_backend.sh`: provisioning backend deployment.

## Common Commands

- Backend tests: run from `platform/backend/` with the repo venv.
- Mobile typecheck/tests: run from `platform/mobile/` with npm scripts.
- Web typecheck/build: run from `platform/web/` with npm scripts.
- ESP32 flash: run `./scripts/flash_esp32.sh --local --port /dev/cu.usbmodem11401 --monitor` from `device/esp32/`.

## Generated / Local-Only Files

- `.venv/`
- `.pio-core/`
- `device/esp32/.pio/`
- `.pantheon/runs/`
- `.pantheon/tasks/`
- `.pantheon/logs/`
- `.pantheon/events/`

## Protected / Core Areas

- Firmware provisioning and Wi-Fi validation paths.
- Backend auth, device registration, and migration code.
- Mobile onboarding flow.
- Deployment scripts and env handling.
