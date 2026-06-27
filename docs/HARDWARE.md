# Hardware

This document records only hardware facts visible in repository code/docs. Physical wiring and board revisions should be re-verified on the bench after moving to a new computer.

## Boards

Verified from `device/esp32/platformio.ini` and firmware docs:

- Master board target: `ESP32-S3-DevKitC-1-N32R16V`.
- Main PlatformIO environments:
  - `esp32-s3-devkitc-1`
  - `esp32-local`
  - `esp32-gcp`
- Camera board target: Seeed Studio XIAO ESP32S3 Sense.
- Camera PlatformIO environments:
  - `camera-test`
  - `camera-platform-test`
  - `espnow-camera-test`
- ESP-NOW master test environment:
  - `espnow-master-test`

## Firmware Versions

Verified in `device/esp32/include/firmware_version.h`:

- Master software version: `0.1.6`
- Master software version code: `1006`
- Camera software version: `0.1.8`
- Camera software version code: `1008`

## Master Pin Map

Verified in `device/esp32/include/config.h`:

| Purpose | GPIO / value |
| --- | --- |
| Soil moisture ADC | GPIO1 |
| DHT22 data | GPIO4 |
| Water temperature OneWire | GPIO5 |
| Water level touch | GPIO13 |
| Optional I2C SDA | GPIO8 |
| Optional I2C SCL | GPIO9 |
| Grow LED MOSFET gate | GPIO15 |
| Legacy pump MOSFET gate | GPIO16 |
| Power/user/touch button | GPIO14 |
| Status LED | GPIO2 |
| ESP-NOW test Wi-Fi channel | 1 |

Needs verification:

- `config.h` marks water sensor defaults as placeholders until confirmed against the wired master board.
- Touch thresholds and moisture calibration defaults need real enclosure/wiring calibration.

## Camera Pin Map

Verified in `device/esp32/src/camera/xiao_camera.cpp`:

| Signal | GPIO |
| --- | --- |
| PWDN | -1 |
| RESET | -1 |
| XCLK | 10 |
| SIOD | 40 |
| SIOC | 39 |
| D7 | 48 |
| D6 | 11 |
| D5 | 12 |
| D4 | 14 |
| D3 | 16 |
| D2 | 18 |
| D1 | 17 |
| D0 | 15 |
| VSYNC | 38 |
| HREF | 47 |
| PCLK | 13 |

## Camera Sensors

Verified in committed code:

- The camera wrapper logs detected sensor PID/name for OV2640, OV3660, and OV5640.
- `PLANTLAB_OV5640_AF_ENABLED` enables the OV5640 autofocus library in the XIAO camera test/platform environments.
- Default camera options use `FRAMESIZE_UXGA`, `PIXFORMAT_JPEG`, JPEG quality `12`, framebuffer count `2`, and PSRAM requirement enabled.
- OV5640 autofocus work is WIP and not fully functional per user report. Treat it as experimental until bench validation passes.

Needs verification:

- Exact installed camera module, lens, and sensor behavior on the current XIAO ESP32S3 hardware.
- Whether the module labeled `DC5640-AF` behaves as expected with the current OV5640 autofocus library.
- Whether OV3660 image quality remains acceptable with the current shared camera wrapper.

## Flash Commands

Build only:

```bash
.venv/bin/pio run -d device/esp32 -e esp32-local
.venv/bin/pio run -d device/esp32 -e esp32-gcp
.venv/bin/pio run -d device/esp32 -e camera-platform-test
.venv/bin/pio run -d device/esp32 -e camera-test
.venv/bin/pio run -d device/esp32 -e espnow-master-test
.venv/bin/pio run -d device/esp32 -e espnow-camera-test
```

Flash examples:

```bash
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --dry-run
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --build-only
./device/esp32/scripts/flash_esp32.sh --local --port /dev/cu.usbmodem11401 --flash
./device/esp32/scripts/flash_esp32.sh --gcp --port /dev/cu.usbmodem11401 --flash
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem12201 --flash --monitor
./device/esp32/scripts/flash_esp32.sh --test-espnow-camera --port /dev/cu.usbmodem12201 --flash --monitor
```

The helper defaults to `--dry-run`. It will not upload to hardware unless
`--flash` is passed.

Needs verification on new computer:

- Serial port names.
- USB driver behavior.
