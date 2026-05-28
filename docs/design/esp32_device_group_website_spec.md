# ESP32 Device Group Website Spec

## Purpose

Define website and platform behavior for an ESP32 PlantLab system where one
user-visible device is made of multiple physical nodes:

- one master node
- zero or more camera nodes

The legacy single-board device runtime has been removed from active device
development. This spec is ESP32-first.

## Core Product Rule

One PlantLab device in the website is a **logical device group**.

That logical device group may contain:

- one ESP32 master node
- one or more ESP32 camera nodes

From the user's perspective, these are still one device.

## Goals

- Keep one dashboard card and one device detail page per PlantLab device.
- Let the master node own commands, device state, and provisioning authority.
- Let camera nodes contribute images and node health without becoming separate
  user-visible devices.
- Allow future support for more than one camera node.
- Keep node details visible for diagnostics without overwhelming normal users.

## Non-Goals

- Do not add a separate user-facing camera provisioning flow.
- Do not make camera nodes appear as standalone devices in the device list.
- Do not add a separate user-facing camera onboarding step.
- Do not expose raw node/protocol details as the default dashboard experience.

## Terminology

### Logical Device

The PlantLab device the user sees and manages in the website.

Owns:

- name
- image gallery
- readings timeline
- commands
- setup/removal lifecycle
- diagnostics timeline

### Hardware Node

A physical board that belongs to a logical device.

Examples:

- ESP32 master node
- ESP32 camera node 1
- ESP32 camera node 2

## Website Data Model

Keep the current `Device` model as the top-level user-owned object.

Use `DeviceNode` / hardware-node records for the internal physical boards.

Core node fields:

- `device_id`
- `hardware_device_id`
- `node_role`
  - `master`
  - `camera`
- `node_index`
- `display_name`
  - `Master`
  - `Camera 1`
- `hardware_model`
  - `plantlab-main-v2`
  - `xiao-esp32s3-camera`
- `hardware_version`
- `software_version`
- `capabilities`
- `status`
- `last_seen_at`

Legacy `single_board` records may exist in old databases, but new onboarding
and simulator flows should use `master` and `camera`.

## Device Behavior Rules

### Master Node Owns

- command polling
- command acknowledgements/results
- logical device state
- actuator state
- provisioning authority
- camera scheduling authority
- device-level readiness for onboarding
- OTA command execution

### Camera Node Owns

- image capture
- image upload
- camera-node heartbeat
- camera-node diagnostics

### User-Facing Rules

- device list shows one card per logical device
- device detail shows one dashboard per logical device
- camera images appear as part of that logical device
- node details appear in diagnostics/support surfaces

## Readiness Rules

If a device has only a master node:

- setup can complete after the master registers and sends initial state

If a device expects a camera node:

- setup should wait until the first image is uploaded
- the dashboard should not show as fully ready before first capture when camera
  capability is expected

## Dashboard Rules

The dashboard should show:

- overall health
- latest image
- primary readings
- grow-light state
- camera state
- recent user-relevant timeline entries

Advanced node details should be available under diagnostics/support surfaces.

## Future Extensions

- multiple camera nodes
- more sensor nodes
- scheduled capture profiles
- local/offline mode
- staged OTA rollout by hardware model and firmware channel
