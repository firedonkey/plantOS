# Local Recovery Scripts

These scripts are for real local PlantLab QA and recovery work against the local backend.

Defaults:

- backend base URL: `http://localhost:8000`
- dev login email: `dev@plantlab.local`
- dev login password: `password`

## Available scripts

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

## Examples

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

## Recovery cookbook

Restart the local backend:

```bash
cd /Users/gary/plantOS
docker compose -f docker-compose.local.yml up -d --build platform
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
