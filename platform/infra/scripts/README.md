# Local Recovery Scripts

These scripts are for real local PlantLab QA and recovery work against the local backend.

Defaults:

- backend base URL: `http://localhost:8000`
- dev login email: `dev@plantlab.local`
- dev login password: `password`

## Available scripts

- `local_status_check.py`
  - one-command local demo status check
  - prints clear `PASS`, `WARN`, and `FAIL` lines
  - checks backend health, one device summary, hardware health, recent readings, recent images, and recent commands
- `hardware_simulator.py`
  - fake hardware loop for backend contract testing
- `backend_health_check.py`
  - checks `/health`
  - optional dev-login smoke
- `device_summary_dump.py`
  - prints one device summary JSON payload
- `command_queue_inspector.py`
  - prints recent commands for one device
- `recent_readings_dump.py`
  - prints recent readings with optional range filters
- `image_upload_inspector.py`
  - prints recent image metadata for one device
- `ota_release.py`
  - builds and publishes ESP32 master and camera OTA releases to the local Docker backend
  - verifies the requested release version matches `device/esp32/include/firmware_version.h`
  - copies firmware artifacts into the backend container's persistent firmware volume and upserts `firmware_releases`

## Examples

Run the one-command local demo status check:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/local_status_check.py --device-id 36
```

Let the script choose the first available device automatically:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/local_status_check.py
```

Check backend health:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/backend_health_check.py --include-dev-login
```

Dump one device summary:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/device_summary_dump.py --device-id 36
```

Inspect the recent command queue:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/command_queue_inspector.py --device-id 36 --limit 12
```

Inspect recent readings:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/recent_readings_dump.py --device-id 36 --limit 8 --order oldest
```

Inspect recent image uploads:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/image_upload_inspector.py --device-id 36 --limit 6
```

Publish a local OTA release for both ESP32 nodes after bumping `firmware_version.h`:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/ota_release.py bump-version \
  --node both \
  --version 0.1.2

.venv/bin/python platform/infra/scripts/ota_release.py publish-local \
  --node both \
  --version 0.1.2 \
  --build
```

Publish only the camera node:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/ota_release.py bump-version \
  --node camera \
  --version 0.1.2

.venv/bin/python platform/infra/scripts/ota_release.py publish-local \
  --node camera \
  --version 0.1.2 \
  --build
```

Check local OTA status:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/ota_release.py status-local
```

Firmware checks OTA once about 60 seconds after boot, then roughly every 6
hours. For immediate OTA testing after publishing a release, reboot or reset the
target ESP32 nodes, then watch serial logs for `[ota] installing release=...`.

List recent local OTA releases:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/ota_release.py list-local-releases
```

## Recovery cookbook

Restart the local backend:

```bash
cd /Users/gary/plantOS
docker compose -f platform/infra/docker/docker-compose.local.yml up -d --build platform
```

Restart Expo with Node 22:

```bash
cd /Users/gary/plantOS/platform/mobile
source ~/.nvm/nvm.sh
nvm use 22
npx expo start --clear --host lan
```

Reflash the master ESP32:

```bash
cd /Users/gary/plantOS/device/esp32
./scripts/flash_esp32.sh --local --monitor
```

Reflash the camera node:

```bash
cd /Users/gary/plantOS/device/esp32
./scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem112201 --monitor
```

Check the current device token:

1. open the standalone device settings page in web or mobile
2. look at the masked token summary
3. if you need the raw token for hardware debugging, fetch the device JSON:

```bash
curl -s http://localhost:8000/api/devices -H 'Authorization: Bearer <DEV_TOKEN>'
```

Check hardware endpoints directly with a device token:

```bash
curl -s http://localhost:8000/api/hardware/commands/pending -H 'X-Device-Token: <DEVICE_TOKEN>'
curl -s -X POST http://localhost:8000/api/hardware/heartbeat -H 'Content-Type: application/json' -H 'X-Device-Token: <DEVICE_TOKEN>' -d '{"status":"online","message":"manual probe"}'
```

## Demo entry points

For a quick local demo bring-up:

1. restart or verify backend:

```bash
cd /Users/gary/plantOS
docker compose -f platform/infra/docker/docker-compose.local.yml up -d --build platform
```

2. start standalone web:

```bash
cd /Users/gary/plantOS/platform/web
npm run dev
```

3. start mobile with Node 22:

```bash
cd /Users/gary/plantOS/platform/mobile
source ~/.nvm/nvm.sh
nvm use 22
npx expo start --clear --host lan
```

4. run the one-command local status check before showing hardware:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/local_status_check.py --device-id 36
```

For broader QA and recovery guidance, also see:

- [LOCAL_RELEASE_CHECKLIST.md](/Users/gary/plantOS/platform/shared/docs/LOCAL_RELEASE_CHECKLIST.md)
- [device/esp32/README.md](/Users/gary/plantOS/device/esp32/README.md)
