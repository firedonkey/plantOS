# PlantLab Current System Design

## Purpose

This document is the current source of truth for the PlantLab hardware and
platform architecture.

PlantLab currently uses ESP32-based devices. The legacy Raspberry Pi runtime has
been removed from the active repository.

## Core Product Rule

One user-visible PlantLab device is one **logical device**.

That logical device is backed by:

- one ESP32-S3 master node
- zero or more ESP32-S3 camera nodes

From the user's perspective, this remains one PlantLab device.

## Current Hardware Architecture

### Master Node

- `ESP32-S3-DevKitC-1-N32R16V`
- sensor reporting
- grow-light control
- BLE provisioning
- Wi-Fi validation
- contract heartbeat and diagnostics
- command polling and command-result reporting
- OTA command execution and OTA status reporting
- camera scheduling authority

### Camera Node

- `Seeed Studio XIAO ESP32-S3 Sense`
- camera capture
- image upload
- camera-node heartbeat and diagnostics
- low-power Wi-Fi operation

The master and camera nodes together represent one PlantLab device.

## Communication Model

- master <-> camera:
  - ESP-NOW for provisioning and capture coordination
- master -> platform:
  - heartbeat
  - sensor readings
  - diagnostics
  - command polling and acknowledgements
  - command completion/failure results
  - OTA status
- camera -> platform:
  - image upload
  - camera-node heartbeat
  - diagnostics

Important rule:

- camera images do **not** route through the master
- camera uploads directly to the platform

## Provisioning Model

The ESP32 master owns the user-facing setup flow.

Current flow:

1. User starts provisioning from the mobile app.
2. Mobile app sends Wi-Fi and backend setup data over BLE.
3. Master validates Wi-Fi and stores pending config.
4. Master registers with the backend as the `master` node.
5. Master provisions the camera node over ESP-NOW.
6. Camera stores runtime config in `Preferences`.
7. Camera joins Wi-Fi and registers as a `camera` node.
8. Master requests image capture.

The camera node is not separately provisioned by the user.

## Website Model

The website treats one PlantLab device as one logical device with one or more
hardware nodes.

Current node roles:

- `master`
- `camera`

Legacy `single_board` records may still exist in old databases, but new device
work should use `master` and `camera`.

Rules:

- device list shows one card per logical device
- device detail page shows one dashboard per logical device
- device detail may show a `Device Components` section for internal nodes
- camera nodes do not appear as separate user-managed devices

## Dashboard Data Ownership

### Master-owned data

- sensor readings
- water state
- grow-light state
- command execution
- runtime state
- OTA state

### Camera-owned data

- latest image
- image gallery entries
- camera-node heartbeat

### Logical device view

The dashboard merges these into one device view:

- one readings panel
- one controls panel
- one image gallery
- one diagnostics timeline

## Setup Finishing Behavior

If there is no camera expected, setup can complete after:

- device exists
- first heartbeat or reading exists

If a camera node is expected:

- setup waits for the first image
- the finishing page should not jump to the dashboard early

This matches the current user expectation:

- onboarding should land on the dashboard with the first image already present

## Camera Node Power Strategy

The current camera-node runtime is low-power but always connected:

- Wi-Fi stays on
- ESP-NOW stays on in STA mode
- Bluetooth is stopped
- idle CPU runs at `80 MHz`
- capture/upload can raise CPU to `160 MHz`
- Wi-Fi power save uses `WIFI_PS_MIN_MODEM`
- Wi-Fi TX power is reduced by config
- camera stays deinitialized until capture is requested

## Current Recommended Docs

For more detail, pair this document with:

- [ESP32 Device Group Website Spec](/Users/gary/plantOS/docs/design/esp32_device_group_website_spec.md)
- [API Contract](/Users/gary/plantOS/docs/design/api_contract.md)
- [Device Protocol](/Users/gary/plantOS/docs/device_protocol.md)
- [Firmware Contract Client](/Users/gary/plantOS/docs/firmware_contract_client.md)
