# PlantLab ESP32 Firmware (v2)

This folder contains PlantLab v2 firmware for ESP32 boards.

Current status:

- Phase 1 started
- DHT22 local reading implemented
- No Wi-Fi/cloud/provisioning/ESP-NOW yet

## Board

- Master board target: `ESP32-S3-DevKitC-1-N32R16V`

## Phase 1 Scope

- Local hardware bring-up only
- Sensor and actuator validation over serial logs

## Current Test

- DHT22 connected to `GPIO4`
- Output over serial every 2 seconds

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

# Flash dedicated DHT22 debug firmware
./scripts/flash_esp32.sh --test-dht22 --monitor

# Flash dedicated moisture ADC debug firmware
./scripts/flash_esp32.sh --test-moisture --monitor

# Flash dedicated light/pump actuator debug firmware
./scripts/flash_esp32.sh --test-actuators --monitor

# Flash dedicated camera-node capture debug firmware
./scripts/flash_esp32.sh --test-camera --port /dev/cu.usbmodem12201 --monitor

# Explicit serial port
./scripts/flash_esp32.sh --port /dev/cu.usbmodem1301 --monitor
```

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
