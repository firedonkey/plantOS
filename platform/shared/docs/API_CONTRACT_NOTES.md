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

- `POST /api/auth/login`
- `GET /auth/login`
- `GET /auth/callback`
- `POST /auth/logout`
- `GET /api/me`

Current state:

- browser session and Google OAuth still power the existing backend-rendered web
- `POST /api/auth/login` is now available as a **dev-only** bearer-token login for local standalone clients
- `GET /api/me` works for either browser session auth or bearer auth from the dev-only login path

Documented next production auth contract:

- `GET /api/auth/google/start`
- `GET /api/auth/google/callback`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/me`

Current note:

- these production standalone auth endpoints are documented, not implemented yet
- the backend remains the intended auth owner for both standalone web and mobile

### Devices

- `GET /api/devices`
- `POST /api/devices`
- `POST /api/devices/setup-code`
- `GET /api/devices/{device_id}`
- `DELETE /api/devices/{device_id}`
- `GET /api/devices/{device_id}/summary`
- `GET /api/devices/{device_id}/readings`
- `GET /api/devices/{device_id}/images/latest`
- `POST /api/devices/{device_id}/factory-reset`
- `POST /api/devices/register-provisioned`

Current purpose:

- user device listing and creation
- onboarding setup-code handoff for standalone clients
- standalone device removal
- client-friendly device summary and latest-image retrieval
- client-friendly reading history retrieval
- device-level provisioning registration proxy
- device reset path for device-authenticated callers

Current shape note:

- `GET /api/devices` remains backward-compatible for existing fields
- it now also includes summary-ready fields for standalone clients:
  - `status`
  - `latest_reading`
  - `latest_image`
  - `node_summary`

Readings history note:

- `GET /api/devices/{device_id}/readings` remains backward-compatible by default:
  - `limit=50`
  - newest-first ordering
- it now also supports standalone-client history queries with:
  - `start=<ISO timestamp>`
  - `end=<ISO timestamp>`
  - `order=newest|oldest`
- standalone web and mobile should prefer `order=oldest` when rendering trend charts so the history array is already aligned left-to-right for the UI

Standalone onboarding note:

- `POST /api/devices/setup-code` is the API replacement for the old backend-rendered `/devices/setup-code` form action
- it returns the verified serial/setup token plus:
  - `continue_setup_url`
  - `setup_finishing_url`
- standalone web uses those URLs to hand off into local device Wi-Fi setup, then return to its own setup-finishing page

### Commands

- `GET /api/devices/{device_id}/commands`
- `POST /api/devices/{device_id}/commands`
- `POST /api/devices/{device_id}/commands/light`
- `POST /api/devices/{device_id}/commands/pump`
- `POST /api/devices/{device_id}/commands/capture`
- `GET /api/devices/{device_id}/commands/pending`
- `POST /api/devices/{device_id}/commands/{command_id}/ack`
- `GET /api/hardware/commands/pending`
- `POST /api/hardware/commands/{command_id}/result`

Current purpose:

- user command creation
- convenience wrappers for light and pump commands used by standalone clients
- device command polling
- device command acknowledgement
- dedicated hardware polling/result reporting using device-token auth

Current wrapper response note:

- standalone wrapper endpoints now use a consistent response envelope:

```json
{
  "status": "accepted",
  "device_id": 30,
  "command": "light",
  "action": "on",
  "message": "Light command queued: turn on.",
  "queued": true,
  "command_id": 42,
  "command_status": "pending",
  "created_at": "2026-05-11T22:00:00Z",
  "value": null
}
```

Current capture note:

- `POST /api/devices/{device_id}/commands/capture` currently returns `501 Not Implemented`
- that is intentional for now; the shared backend command queue does not yet support a real capture command contract
- the `501` response now uses the standard API error envelope and includes a `future_response` example in `error.details`
- web and mobile should currently present manual capture as postponed or coming later, rather than as a broken action

Current hardware polling note:

- `GET /api/hardware/commands/pending` returns only commands for the authenticated device token
- hardware polling claims commands by moving them from `pending` to `in_progress`
- hardware completion is reported with `POST /api/hardware/commands/{command_id}/result`
- result statuses currently supported there are:
  - `in_progress`
  - `completed`
  - `failed`

### Sensor readings

- `POST /api/data`
- `POST /api/hardware/readings`

Current purpose:

- ingest device readings
- dedicated hardware-ingest path for device-token clients

Current note:

- grouped devices that include camera nodes require `hardware_device_id` on reading ingest
- `POST /api/hardware/readings` infers `device_id` from the device token, so hardware clients do not need to include it in the payload

### Images

- `POST /api/image`
- `GET /api/images/{image_id}/content`
- `GET /api/devices/{device_id}/images/latest`
- `GET /api/devices/{device_id}/images`

Current purpose:

- image upload from device or node
- image content fetch for signed-in browser users
- recent image gallery fetch for standalone web and mobile

Current note:

- image upload accepts optional `source_hardware_device_id`
- `GET /api/devices/{device_id}/images` returns recent images newest first
- `limit` is optional, defaults to `12`, and is capped at `50`
- standalone web and mobile should prefer the image-list endpoint for gallery UI, and keep `images/latest` as a compatibility fallback for older local backends

### Device nodes

- `POST /api/device-nodes/register`
- `POST /api/device-nodes/heartbeat`

Current purpose:

- register grouped hardware nodes such as camera nodes
- track node heartbeat and status

Current migration note:

- camera-style secondary nodes still register through `POST /api/device-nodes/register`
- new ESP32 camera heartbeat/status traffic should prefer `POST /api/hardware/heartbeat`
- the older `/api/device-nodes/heartbeat` route remains available for backward compatibility during migration

### Device status

- `POST /api/status`
- `POST /api/hardware/heartbeat`

Current purpose:

- device-level status heartbeat path
- dedicated hardware heartbeat path using device-token auth

Current heartbeat note:

- `POST /api/hardware/heartbeat` can update device status fields
- if `hardware_device_id` is provided for a registered node, it also updates the node `last_seen_at`
- ESP32 camera-node firmware now uses `POST /api/hardware/heartbeat` after registration while keeping image upload and node registration on their existing routes

## Hardware command polling contract

### Device token auth

Hardware endpoints use:

- `X-Device-Token: <device api token>`

They do not use:

- user bearer auth
- browser session auth

### Hardware endpoints

- `POST /api/hardware/readings`
- `GET /api/hardware/commands/pending`
- `POST /api/hardware/commands/{command_id}/result`
- `POST /api/hardware/heartbeat`

### Command lifecycle

- `pending`
  - created by web/mobile/backend user APIs
- `in_progress`
  - claimed by `/api/hardware/commands/pending`
  - may also be re-reported explicitly by `/api/hardware/commands/{command_id}/result`
- `completed`
  - reported by hardware after successful execution
- `failed`
  - reported by hardware when execution fails
- `timed_out`
  - backend fallback for stale commands

### Example curl commands

Upload a reading:

```bash
curl -X POST http://localhost:8000/api/hardware/readings \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Token: DEVICE_TOKEN' \
  -d '{
    "moisture": 42.1,
    "temperature": 22.5,
    "humidity": 51.0,
    "light_on": false,
    "pump_on": false
  }'
```

Poll pending commands:

```bash
curl http://localhost:8000/api/hardware/commands/pending \
  -H 'X-Device-Token: DEVICE_TOKEN'
```

Report a completed command:

```bash
curl -X POST http://localhost:8000/api/hardware/commands/123/result \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Token: DEVICE_TOKEN' \
  -d '{
    "status": "completed",
    "message": "light on",
    "light_on": true,
    "pump_on": false
  }'
```

Send a heartbeat:

```bash
curl -X POST http://localhost:8000/api/hardware/heartbeat \
  -H 'Content-Type: application/json' \
  -H 'X-Device-Token: DEVICE_TOKEN' \
  -d '{
    "status": "online",
    "message": "hardware loop healthy"
  }'
```

### Example hardware payloads

ESP32-style reading payload:

```json
{
  "hardware_device_id": "master-01",
  "moisture": 39.8,
  "temperature": 23.0,
  "humidity": 53.1,
  "light_on": false,
  "pump_on": false,
  "pump_status": "idle"
}
```

Python command result payload:

```json
{
  "status": "failed",
  "error": "pump jam detected"
}
```

## Current backend-rendered JSON endpoints still living under web routes

These are useful today, but they are not final standalone-client API endpoints:

- `GET /devices/{device_id}/summary.json`
- `GET /setup/status.json`

Why they matter:

- they already provide browser-facing data for the current dashboard and setup flow
- they are implemented under backend web routes, not under a standalone API namespace

Standalone replacements now available:

- `GET /api/setup/status`
- `GET /api/devices/{device_id}/summary`

## Remaining contract gaps for standalone web and mobile

### 1. Production-ready standalone auth contract

Current state:

- a dev-only bearer login now exists for local standalone clients
- production auth is still browser-session / Google-OAuth oriented

Needed later:

- standalone Google-start and callback endpoints for standalone clients
- backend-issued short-lived access tokens
- backend-owned refresh-token/session contract
- clear logout and token-rotation behavior
- clear rollout rules for web/mobile auth beyond local dev

### 2. Capture command device support

Current state:

- light and pump convenience wrappers now exist
- capture convenience endpoint exists but intentionally returns `501 Not Implemented`
- the future accepted response is now documented in the error payload

Needed later:

- implement device-side support for a queued `capture` command so the backend can move from `unsupported` to `accepted`

## Setup/onboarding API responses

### `POST /api/devices/setup-code`

Current standalone response shape:

```json
{
  "serial_number": "SN-ESP32-001",
  "setup_code": null,
  "claim_token": "claim-esp32-001",
  "setup_token": "claim-esp32-001",
  "local_setup_url": "http://10.42.0.1:8080/",
  "provisioning_api_url": "http://localhost:3000",
  "platform_url": "http://localhost:8000",
  "setup_finishing_url": "http://localhost:5173/devices/setup-finishing?device_name=Device+1&location=Kitchen&expect_image=1",
  "continue_setup_url": "http://10.42.0.1:8080/?setup_code=claim-esp32-001&sn=SN-ESP32-001&device_name=Device+1&location=Kitchen&backend_url=http%3A%2F%2Flocalhost%3A3000&platform_url=http%3A%2F%2Flocalhost%3A8000&return_url=http%3A%2F%2Flocalhost%3A5173%2Fdevices%2Fsetup-finishing%3Fdevice_name%3DDevice%2B1%26location%3DKitchen%26expect_image%3D1",
  "expect_image": true
}
```

### `GET /api/setup/status`

Current standalone response shape:

```json
{
  "ready": true,
  "device_found": true,
  "device_id": 30,
  "has_reading": true,
  "has_image": true,
  "expect_image": true,
  "redirect_path": "/devices/30?setup=complete"
}
```

## Standard API error envelope

All `/api/*` routes now return a consistent error envelope for API and validation errors:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": {
      "errors": []
    }
  }
}
```

Notes:

- backend-rendered non-API routes are intentionally unchanged
- old browser flows still rely on their existing responses

## Standard standalone command envelope

The standalone wrapper endpoints currently return:

```json
{
  "status": "accepted" | "unsupported" | "error",
  "device_id": 30,
  "command": "light" | "pump" | "capture",
  "action": "on" | "off" | "run" | "capture",
  "message": "Human-readable command status",
  "queued": true,
  "command_id": 42,
  "command_status": "pending",
  "created_at": "2026-05-11T22:00:00Z",
  "value": "7"
}
```

## Current safe contract for client planning

For the immediate next steps:

- treat the existing backend endpoints as the authoritative runtime surface for devices
- treat web-route JSON endpoints as transitional
- standalone mobile can use the dev-only bearer login for local development
- do not treat the dev-only login as the final production auth design
- treat the documented production auth endpoints as the next implementation target, not as live endpoints yet

## Migration rule

Stabilize the API contract before depending on it from `platform/mobile`.
