# PlantLab ESP32 Firmware (v2)

This folder contains PlantLab v2 firmware for ESP32 boards.

Current status:

- Phase 1 started
- DHT22 local reading implemented
- Power button + status LED state handling implemented in main firmware
- Local Wi-Fi + platform HTTP path now available for dev testing
- ESP32 master provisioning now mirrors the Raspberry Pi user flow

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
  - Long press 10s: factory reset requested log

## Current Test

- DHT22 connected to `GPIO4`
- Output over serial every 2 seconds

## Local platform smoke test

The ESP32 branch now mirrors the Raspberry Pi device contract for:

- `POST /api/data`
- `POST /api/devices/{device_id}/status`
- `GET /api/devices/{device_id}/commands/pending`
- `POST /api/devices/{device_id}/commands/{command_id}/ack`
- `POST /api/image`

Start the local stack first:

```bash
cd /Users/gary/plantOS
docker compose --env-file .env.local -f docker-compose.local.yml up --build -d
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

For the normal Add Device provisioning flow, the website now supplies:

- setup code
- platform URL
- return URL

so the firmware does not rely on hardcoded local-vs-GCP URLs during onboarding.

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

This change is ESP32-only and does not alter the Raspberry Pi path.

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
- sends sensor readings to the platform
- sends status heartbeats
- polls and acknowledges light/pump commands

Camera uploader firmware (`camera-platform-test`) now:

- runs on the XIAO ESP32-S3 Sense
- captures JPEG frames
- uploads images to the same platform device using the same device token

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
2. Confirm sensor readings begin showing on the device page.
3. Use the web dashboard to send a light or pump command.
4. Flash the XIAO camera board with `camera-platform-test`.
5. Confirm images begin appearing for the same device.

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
