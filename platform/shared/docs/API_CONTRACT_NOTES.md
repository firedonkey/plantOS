# API Contract Notes

## Purpose

This document records the current PlantLab backend API surface after the Stage 1 safe move.

It is intended to guide:

- the future standalone `platform/web` app
- the future Expo `platform/mobile` app
- later OpenAPI and shared-type work under `platform/shared`

## Current API endpoints already present

### Health

- `GET /api/health`
- `GET /health`

Current purpose:

- local smoke verification
- deployment and runtime health checks

### Auth and current user

- `GET /auth/login`
- `GET /auth/callback`
- `POST /auth/logout`
- `GET /api/me`

Current state:

- browser-session oriented
- suitable for the existing backend-rendered web
- not yet a standalone token-based client auth contract

### Devices

- `GET /api/devices`
- `POST /api/devices`
- `GET /api/devices/{device_id}`
- `POST /api/devices/{device_id}/factory-reset`
- `POST /api/devices/register-provisioned`

Current purpose:

- user device listing and creation
- device-level provisioning registration proxy
- device reset path for device-authenticated callers

### Commands

- `GET /api/devices/{device_id}/commands`
- `POST /api/devices/{device_id}/commands`
- `GET /api/devices/{device_id}/commands/pending`
- `POST /api/devices/{device_id}/commands/{command_id}/ack`

Current purpose:

- user command creation
- device command polling
- device command acknowledgement

### Sensor readings

- `POST /api/data`

Current purpose:

- ingest device readings

Current note:

- grouped devices that include camera nodes require `hardware_device_id` on reading ingest

### Images

- `POST /api/image`
- `GET /api/images/{image_id}/content`

Current purpose:

- image upload from device or node
- image content fetch for signed-in browser users

Current note:

- image upload accepts optional `source_hardware_device_id`

### Device nodes

- `POST /api/device-nodes/register`
- `POST /api/device-nodes/heartbeat`

Current purpose:

- register grouped hardware nodes such as camera nodes
- track node heartbeat and status

### Device status

- `POST /api/status`

Current purpose:

- device-level status heartbeat path

## Current backend-rendered JSON endpoints still living under web routes

These are useful today, but they are not final standalone-client API endpoints:

- `GET /devices/{device_id}/summary.json`
- `GET /setup/status.json`

Why they matter:

- they already provide browser-facing data for the current dashboard and setup flow
- they are implemented under backend web routes, not under a standalone API namespace

## Current contract gaps for standalone web and mobile

### 1. Standalone auth contract

Current gap:

- browser login is session and redirect based
- mobile-friendly token login is not defined yet

Needed later:

- a dev-only placeholder token auth path for local standalone clients
- clear current-user contract for token-authenticated clients

### 2. Device summary endpoint for clients

Current gap:

- dashboard summary currently lives at `/devices/{device_id}/summary.json`
- it is not yet a formal client API endpoint under `/api/...`

Needed later:

- a stable device summary endpoint for web and mobile

Suggested direction:

- `GET /api/devices/{device_id}/summary`

### 3. Reading history endpoint for clients

Current gap:

- reading ingest exists
- client-facing history retrieval is still mostly assembled through backend web logic

Needed later:

- stable client history endpoint

Suggested direction:

- `GET /api/devices/{device_id}/readings`

### 4. Image list endpoint for clients

Current gap:

- image upload exists
- image content retrieval exists
- image list and latest-image retrieval are not yet formal standalone-client endpoints

Needed later:

- stable client image-list endpoint

Suggested direction:

- `GET /api/devices/{device_id}/images`
- `GET /api/devices/{device_id}/images/latest`

### 5. Setup flow status endpoint

Current gap:

- setup-finishing currently relies on backend web flow

Needed later:

- API contract for setup or onboarding progress if standalone web reproduces the current flow

### 6. Command convenience endpoints

Current state:

- command creation exists through the commands collection endpoint

Possible future convenience:

- domain-specific wrappers for capture image, light control, and pump control if that improves client ergonomics

This is optional and should not be added unless it simplifies the standalone clients meaningfully.

## Current safe contract for client planning

For the immediate next steps:

- treat the existing backend endpoints as the authoritative runtime surface for devices
- treat web-route JSON endpoints as transitional
- do not promise token-authenticated standalone clients until the auth step is implemented

## Migration rule

Stabilize the API contract before depending on it from `platform/mobile`.
