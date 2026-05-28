# PlantLab ESP32 Firmware (v2)

This folder contains PlantLab v2 firmware for ESP32 boards.

Current status:

- Phase 1 started
- DHT22 local reading implemented
- Power button + status LED state handling implemented in main firmware
- Local Wi-Fi + platform HTTP path now available for dev testing
- ESP32 master provisioning is the active PlantLab device onboarding path

## Board

- Master board target: `ESP32-S3-DevKitC-1-N32R16V`

## Phase 1 Scope

- Local hardware bring-up only
- Sensor and actuator validation over serial logs
- Power button behavior:
  - Short press: enter deep sleep
  - Long press: enter provisioning placeholder mode
- Capacitive touch button behavior on GPIO14:
  - Short tap: toggle light
  - Double tap: camera capture request log
  - Long press 5s: provisioning trigger requested log
  - Long press 15s: factory reset requested log

## Current Test

- DHT22 connected to `GPIO4`
- Output over serial every 2 seconds

## Local platform smoke test

The ESP32 master firmware now uses the dedicated hardware contract with device-token auth:

- `POST /api/hardware/readings`
- `POST /api/hardware/heartbeat`
- `GET /api/hardware/commands/pending`
- `POST /api/hardware/commands/{command_id}/result`

The camera-node flow keeps its existing registration and image upload paths:

- `POST /api/image`
- `POST /api/device-nodes/register`
- `POST /api/hardware/heartbeat`

Start the local stack first:

```bash
cd /Users/gary/plantOS
docker compose --env-file platform/infra/env/.env.local -f platform/infra/docker/docker-compose.local.yml up --build -d
```

Health check:

```bash
curl http://localhost:8000/health
```

Before flashing, copy:

```bash
cp /Users/gary/plantOS/device/esp32/include/platform_secrets.example.h \
  /Users/gary/plantOS/device/esp32/include/platform_secrets.h
```

Then edit `platform_secrets.h` with:

- fallback Wi-Fi / platform values for direct smoke tests
- local or cloud defaults if you want a backup when not using Add Device
- `PLANTLAB_PLATFORM_URL`
- `PLANTLAB_DEVICE_ID`
- `PLANTLAB_DEVICE_TOKEN`

For the normal Add Device provisioning flow, the website now supplies:

- setup code
- provisioning backend URL
- platform URL
- return URL

so the firmware does not rely on hardcoded local-vs-GCP URLs during onboarding.
The setup page now posts those values back as hidden form fields, which makes the browser handoff more reliable on the ESP32 access-point network.

## BLE provisioning

BLE provisioning is the default setup path for the ESP32 master when no Wi-Fi
credentials are saved. Long-press the provisioning button on `GPIO14` to enter
BLE provisioning on an already configured device. The status LED on `GPIO2`
uses the provisioning blink pattern while BLE setup is active.

The firmware advertises as `PlantLab-Setup-<suffix>` and exposes:

- Service UUID: `c7d36f9a-7b18-4c52-9c4f-93c2f0f6a901`
- Write characteristic UUID: `c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902`
- Status characteristic UUID: `c7d36f9a-7b18-4c52-9c4f-93c2f0f6a903`

Write one compact JSON payload to the write characteristic:

```json
{
  "ssid": "HomeWiFi",
  "password": "wifi-password",
  "plantlab_token": "setup-or-claim-token",
  "platform_url": "https://platform.example",
  "backend_url": "https://provisioning.example"
}
```

Required fields are `ssid`, `password`, and `plantlab_token`. `platform_url`
may be omitted only when the firmware has `PLANTLAB_PLATFORM_URL` configured.
Accepted aliases are `wifi_ssid`, `wifi_password`, `setup_code`, and
`claim_token`. The token is the PlantLab setup/claim token; direct long-term
`device_access_token` provisioning is intentionally rejected.

The status characteristic returns JSON such as:

```json
{"state":"PROVISIONING_BLE","ready":true}
{"state":"WIFI_CONNECTING","ready":false}
{"state":"PROVISIONING_BLE","ready":true,"error":"wifi_connect_failed"}
{"state":"PROVISIONING_SUCCESS","ready":false,"rebooting":true}
```

After a valid BLE payload is received, the device first validates the supplied
Wi-Fi SSID and password while BLE stays active. If Wi-Fi cannot be joined, the
status characteristic returns to `PROVISIONING_BLE` with `ready:true` and an
error such as `wifi_connect_failed`, `wifi_connect_timeout`, or
`wifi_network_not_found`, so the mobile app can let the user edit the password
without waiting for backend polling. Only after Wi-Fi validation succeeds does
the firmware save the pending config to ESP32 NVS, notify success, reboot,
exchange the claim token through the existing
`/api/devices/register-provisioned` backend flow, and resume hardware
heartbeats with the returned device token. Wi-Fi passwords and full tokens are
not printed to serial logs.

You can send the payload with nRF Connect, LightBlue, or Web Bluetooth. Minimal
Web Bluetooth example:

```js
const service = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a901";
const writeChar = "c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902";
const device = await navigator.bluetooth.requestDevice({
  filters: [{ namePrefix: "PlantLab-Setup-" }],
  optionalServices: [service],
});
const server = await device.gatt.connect();
const svc = await server.getPrimaryService(service);
const ch = await svc.getCharacteristic(writeChar);
await ch.writeValue(new TextEncoder().encode(JSON.stringify({
  ssid: "HomeWiFi",
  password: "wifi-password",
  plantlab_token: "setup-or-claim-token",
  platform_url: "https://platform.example"
})));
```

SoftAP provisioning remains compiled in and is used as a fallback if BLE setup
cannot be started.

## Main firmware environment selection

The main ESP32 master firmware now has explicit environment targets:

- `esp32-local`
- `esp32-gcp`
- `esp32-s3-devkitc-1` (neutral/default)

These targets all use the same provisioning logic. The difference is intent and
clearer serial logging, so you can tell what you flashed.

Recommended usage:

```bash
# Local testing
./scripts/flash_esp32.sh --local --monitor

# GCP testing
./scripts/flash_esp32.sh --gcp --monitor
```

For local dev, the quickest way to get `device_id` and `api_token` is:

1. Sign in to the local web app and add a device once.
2. Query the local Postgres container:

```bash
docker exec -it plantlab-local-postgres \
  psql -U plantlab_user -d plantlab \
  -c "select id, name, api_token from devices order by id desc;"
```

Use that `id` as `PLANTLAB_DEVICE_ID` and the `api_token` as `PLANTLAB_DEVICE_TOKEN`.

Main firmware (`esp32-s3-devkitc-1`) now:

- connects to Wi-Fi
- sends sensor readings to `POST /api/hardware/readings`
- sends status heartbeats to `POST /api/hardware/heartbeat`
- polls `GET /api/hardware/commands/pending`
- reports command results to `POST /api/hardware/commands/{command_id}/result`
- forwards queued manual capture commands to the camera node over the existing ESP-NOW capture path
- reports capture `in_progress`, `completed`, or `failed` back to the backend based on the camera acknowledgement/upload result

Camera uploader firmware (`camera-platform-test`) now:

- runs on the XIAO ESP32-S3 Sense
- captures JPEG frames
- uploads images to the same platform device using the same device token
- returns camera-side capture acknowledgements to the master after upload success or failure

## Local OTA release helper

The local OTA helper publishes firmware releases into the Docker backend for
master and camera OTA testing. Before publishing, bump the matching constants in
`include/firmware_version.h`; the helper refuses to publish a release whose
requested version does not match the compiled firmware version.

Start the local backend first:

```bash
cd /Users/gary/plantOS
docker compose -f platform/infra/docker/docker-compose.local.yml up -d --build
```

Prepare and publish master and camera firmware:

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

Check device OTA progress:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/ota_release.py status-local
```

Devices poll the OTA manifest during normal runtime. Watch serial logs for
`[ota] installing release=...` and the boot-time firmware version line after
the update reboots. The current firmware checks once about 60 seconds after
boot, then roughly every 6 hours, so reboot or reset the node when you want to
test a newly published OTA release immediately.

Dedicated Wi-Fi test firmware (`wifi-test`) now:

- runs on the XIAO ESP32-S3
- only tests Wi-Fi join and retry behavior
- prints:
  - target SSID
  - current Wi-Fi status
  - assigned IP
  - gateway
  - RSSI

That gives us a local end-to-end split matching the current ESP32 hardware split:

- master board -> readings + commands
- camera board -> images

Suggested smoke-test order:

1. Flash the master board with the default firmware.
2. Confirm serial logs show:
   - Wi-Fi connected
   - reading upload success
   - heartbeat success
3. Confirm sensor readings begin showing on the standalone web or mobile dashboard.
4. Use the web dashboard to send a light or pump command and confirm:
   - the command appears in serial output
   - the actuator runs
   - the command activity panel updates to completed
5. Use the web or mobile dashboard to send a manual capture command and confirm:
   - the master logs the queued capture command
   - the camera node captures and uploads a JPEG
   - the command activity panel moves through `in_progress` to `completed`
   - the recent image gallery refreshes with the new image
6. Flash the XIAO camera board with `camera-platform-test`.
7. Confirm images begin appearing for the same device.

## Manual capture debug checklist

When a manual capture does not complete cleanly, keep both serial monitors open and trigger
`Capture Image` from the standalone web or mobile dashboard.

Master serial should now show:

- backend capture command id
- ESP-NOW capture `request_id`
- target MAC used for the request
- `in_progress` update sent to the backend
- camera ACK status, echoed command id, and capture/upload elapsed time
- explicit timeout log if no ACK is received in time

Camera serial should now show:

- capture request received with `request_id` and echoed backend command id
- queue wait before capture starts
- upload start with request id and JPEG byte count
- upload HTTP result and elapsed time
- ACK sent back to the master with the echoed backend command id

Recommended local debug flow:

1. Flash the master:

```bash
cd /Users/gary/plantOS/device/esp32
./scripts/flash_esp32.sh --local --port /dev/cu.usbmodem11401 --monitor
```

2. Flash the camera node in another terminal:

```bash
cd /Users/gary/plantOS/device/esp32
./scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem112201 --monitor
```

3. Trigger `Capture Image` once.
4. Match the backend command id from the UI/API with:
   - the master `capture command <id> forwarded to camera request=<request_id>` log
   - the camera `command_id=<id> request=<request_id>` log
   - the master ACK/result log for the same request

If the gallery updates but the command fails, compare:

- master timeout timestamp
- camera upload completion timestamp
- whether the camera sent the ACK after upload

That will distinguish:

- camera never received the request
- camera captured but upload failed
- upload succeeded but ACK was lost
- ACK arrived too late for the current timeout budget

## Build/Flash (PlatformIO)

1. Install PlatformIO Core in `/Users/gary/plantOS/.venv`.
2. From this folder run:

```bash
export PLATFORMIO_CORE_DIR=/Users/gary/plantOS/.pio-core
pio run
pio run -t upload
pio device monitor -b 115200
```

## One-command flash script

Use:

```bash
cd /Users/gary/plantOS/device/esp32
./scripts/flash_esp32.sh
```

Common options:

```bash
# Flash + open serial monitor
./scripts/flash_esp32.sh --monitor

# Flash main firmware with explicit local profile
./scripts/flash_esp32.sh --local --monitor

# Flash main firmware with explicit GCP profile
./scripts/flash_esp32.sh --gcp --monitor

# Flash dedicated DHT22 debug firmware
./scripts/flash_esp32.sh --test-dht22 --monitor

# Flash dedicated moisture ADC debug firmware
./scripts/flash_esp32.sh --test-moisture --monitor

# Flash dedicated light/pump actuator debug firmware
./scripts/flash_esp32.sh --test-actuators --monitor

# Flash dedicated camera-node capture debug firmware
./scripts/flash_esp32.sh --test-camera --port /dev/cu.usbmodem12201 --monitor

# Flash camera-node platform uploader firmware
./scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem12201 --monitor

# Flash dedicated XIAO Wi-Fi test firmware
./scripts/flash_esp32.sh --test-wifi --port /dev/cu.usbmodem12201 --monitor

# Flash dedicated touch-button debug firmware (clean event-only output)
./scripts/flash_esp32.sh --test-touch --monitor

# Flash ESP-NOW link test (master board)
./scripts/flash_esp32.sh --test-espnow-master --port /dev/cu.usbmodem1301 --monitor

# Flash ESP-NOW link test (camera board)
./scripts/flash_esp32.sh --test-espnow-camera --port /dev/cu.usbmodem12201 --monitor

# Explicit serial port
./scripts/flash_esp32.sh --port /dev/cu.usbmodem1301 --monitor
```

ESP-NOW master serial keys:

- `c` -> send `capture_image` command
- `p` -> send `provision_start` command (placeholder)
- `h` -> send `health_check` command

## Phase 1 stress gate

Use the automated stress harness:

```bash
cd /Users/gary/plantOS/device/esp32
source /Users/gary/plantOS/.venv/bin/activate
python scripts/phase1_stress_test.py \
  --master-port /dev/cu.usbmodem1301 \
  --camera-port /dev/cu.usbmodem12201 \
  --duration 1800
```

Detailed checklist:

- `/Users/gary/plantOS/device/esp32/PHASE1_STRESS_TEST.md`

## Camera SD commands (camera-test firmware)

In serial monitor:

- `c` then Enter: capture and save a JPEG to SD card
- `l` then Enter: list files on SD card
- `d /capture_0.jpg` then Enter: dump file bytes over serial

## Export image from SD without removing card

From your laptop:

```bash
cd /Users/gary/plantOS/device/esp32
python scripts/export_sd_image.py \
  --port /dev/cu.usbmodem12201 \
  --path /capture_0.jpg \
  --out /Users/gary/Desktop/capture_0.jpg
```

If needed, install dependency once:

```bash
source /Users/gary/plantOS/.venv/bin/activate
python -m pip install pyserial
```
