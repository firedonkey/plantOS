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

### Devices

- `GET /api/devices`
- `POST /api/devices`
- `GET /api/devices/{device_id}`
- `GET /api/devices/{device_id}/summary`
- `GET /api/devices/{device_id}/readings`
- `GET /api/devices/{device_id}/images/latest`
- `POST /api/devices/{device_id}/factory-reset`
- `POST /api/devices/register-provisioned`

Current purpose:

- user device listing and creation
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

### Commands

- `GET /api/devices/{device_id}/commands`
- `POST /api/devices/{device_id}/commands`
- `POST /api/devices/{device_id}/commands/light`
- `POST /api/devices/{device_id}/commands/pump`
- `POST /api/devices/{device_id}/commands/capture`
- `GET /api/devices/{device_id}/commands/pending`
- `POST /api/devices/{device_id}/commands/{command_id}/ack`

Current purpose:

- user command creation
- convenience wrappers for light and pump commands used by standalone clients
- device command polling
- device command acknowledgement

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

## Remaining contract gaps for standalone web and mobile

### 1. Production-ready standalone auth contract

Current state:

- a dev-only bearer login now exists for local standalone clients
- production auth is still browser-session / Google-OAuth oriented

Needed later:

- a production-ready token or equivalent standalone auth contract
- clear rollout rules for web/mobile auth beyond local dev

### 2. Full image-list endpoint for clients

Current state:

- image upload exists
- image content retrieval exists
- latest-image retrieval now exists at `GET /api/devices/{device_id}/images/latest`

Needed later:

- stable image-list endpoint if standalone clients need more than the latest image

Suggested direction:

- `GET /api/devices/{device_id}/images`

### 3. Setup flow status endpoint

Current gap:

- setup-finishing currently relies on backend web flow

Needed later:

- API contract for setup or onboarding progress if standalone web reproduces the current flow

### 4. Capture command device support

Current state:

- light and pump convenience wrappers now exist
- capture convenience endpoint exists but intentionally returns `501 Not Implemented`
- the future accepted response is now documented in the error payload

Needed later:

- implement device-side support for a queued `capture` command so the backend can move from `unsupported` to `accepted`

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

## Migration rule

Stabilize the API contract before depending on it from `platform/mobile`.
