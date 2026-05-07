# PlantLab Current System Design

## Purpose

This document is the current source of truth for the PlantLab hardware and platform architecture.

It reflects the latest working system in this repository, including:

- Raspberry Pi single-board devices
- ESP32 master + camera-node grouped devices
- shared website behavior for both hardware families

## Core Product Rule

One user-visible PlantLab device is one **logical device**.

That logical device may be backed by:

- one Raspberry Pi board
- one ESP32 master node
- one ESP32 master node plus one or more ESP32 camera nodes

From the user's perspective, these are all still just one PlantLab device.

## Current Hardware Architecture

### Raspberry Pi path

Current Raspberry Pi devices are single-board systems:

- sensors
- camera
- actuators
- provisioning flow
- backend communication

all live on the same board.

### ESP32 path

Current ESP32 systems are split into:

- **Master node**
  - `ESP32-S3-DevKitC-1-N32R16V`
  - moisture sensor
  - DHT22
  - light control
  - pump control
  - provisioning button
  - PlantLab SoftAP setup host
  - command execution
  - camera scheduling authority

- **Camera node**
  - `Seeed Studio XIAO ESP32-S3 Sense`
  - camera capture
  - image upload
  - node heartbeat
  - low-power always-connected Wi-Fi operation

The master and camera nodes together still represent one PlantLab device in the website.

## Communication Model

### Raspberry Pi

- Wi-Fi -> platform
- single board owns readings, images, and commands

### ESP32 master + camera

- master <-> camera:
  - ESP-NOW for provisioning and capture coordination
- master -> platform:
  - sensor readings
  - command polling and acknowledgements
  - device-level status
- camera -> platform:
  - image upload
  - camera-node heartbeat

Important rule:

- camera images do **not** route through the master
- camera uploads directly to the platform

## Provisioning Model

### Shared user-facing flow

The user provisions only one device.

High-level flow:

1. User clicks **Add Device**
2. User verifies the serial number
3. User joins `PlantLab-Setup`
4. User enters home Wi-Fi once
5. PlantLab finishes setup

### Raspberry Pi provisioning

The Raspberry Pi performs its own SoftAP onboarding and then registers as a single-board device.

### ESP32 provisioning

The ESP32 master owns the user-facing setup flow.

Current flow:

1. User long-presses the master button
2. Master starts SoftAP at `http://10.42.0.1:8080`
3. User enters Wi-Fi once
4. Master joins home Wi-Fi
5. Master registers as a `master` node
6. Master provisions the camera node over ESP-NOW
7. Camera stores runtime config in `Preferences`
8. Camera joins Wi-Fi and registers as a `camera` node
9. Master requests image capture

The camera node is not separately provisioned by the user.

## Website Model

The website treats one PlantLab device as one logical device with one or more hardware nodes.

Current node roles:

- `single_board`
- `master`
- `camera`

Rules:

- device list shows one card per logical device
- device detail page shows one dashboard per logical device
- device detail may show a `Device Components` section for internal nodes
- camera nodes do not appear as separate user-managed devices

## Dashboard Data Ownership

### Master-owned data

- soil moisture
- temperature
- humidity
- growing light state
- pump state
- command execution

### Camera-owned data

- latest image
- image gallery entries
- camera-node heartbeat

### Logical device view

The dashboard merges these into one device view:

- one readings panel
- one controls panel
- one image gallery

## Setup Finishing Behavior

### Raspberry Pi

Setup completes when:

- device exists
- first reading exists
- first image exists

### ESP32 master-only path

If there is no camera expected, setup can complete after:

- device exists
- first reading exists

### ESP32 master + camera path

Current working behavior:

- setup waits for the first image when camera capture is expected
- the finishing page should not jump to the dashboard early

This matches the current user expectation for ESP32 grouped devices:

- onboarding should land on the dashboard with the first image already present

## Master-Controlled Camera Scheduling

The master owns the image schedule.

Current behavior:

- master sends `capture_image` commands over ESP-NOW
- camera captures only when requested
- camera stays connected to Wi-Fi between captures
- camera initializes the camera only during capture/upload
- camera deinitializes the camera afterward

Current default capture interval:

- `15000 ms` (15 seconds)

### First-image reliability behavior

The current onboarding path includes first-image hardening:

- provisioning ACK path
- bootstrap capture retries
- direct targeting of the learned camera MAC once available
- readiness promotion after successful capture ACK

This is intended to make the first dashboard image appear during setup, not long after it.

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

## Current Tradeoffs

### Raspberry Pi

- simpler single-board behavior
- higher hardware cost
- less modular

### ESP32

- cheaper and more modular
- better multi-camera future
- more coordination complexity between master and camera nodes

## Current Recommended Docs

For more detail, pair this document with:

- [ESP32 Device Group Website Spec](/Users/gary/plantOS/docs/design/esp32_device_group_website_spec.md)
- [API Contract](/Users/gary/plantOS/docs/design/api_contract.md)
- [SoftAP Provisioning Design](/Users/gary/plantOS/docs/design/softap_provisioning_design.md)
