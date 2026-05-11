# Backend and Web Coupling Inventory

## Purpose

This document records the current backend and web coupling after the Stage 1 safe move.

The goal is to make the remaining separation work explicit before building the standalone `platform/web` app.

## Current state

During Stage 1:

- the backend code now lives under `platform/backend`
- the current browser experience still lives inside the backend
- backend still serves:
  - server-rendered routes
  - Jinja templates
  - static CSS and assets

This is intentional and temporary.

## Backend-owned pieces that are already reusable

These pieces are already on the API side and are natural candidates for reuse by standalone web and mobile clients:

- `/api/health`
- `/health`
- `/api/me`
- `/api/devices`
- `/api/devices/{device_id}`
- `/api/devices/{device_id}/commands`
- `/api/devices/{device_id}/commands/pending`
- `/api/devices/{device_id}/commands/{command_id}/ack`
- `/api/devices/register-provisioned`
- `/api/data`
- `/api/image`
- `/api/images/{image_id}/content`
- `/api/device-nodes/register`
- `/api/device-nodes/heartbeat`
- `/api/status`

These endpoints cover:

- health checks
- device registration and ingest
- command flow
- image upload
- grouped node registration and heartbeat

## Browser flows still coupled to backend-rendered pages

These flows still depend on backend web routes and templates:

- `/`
- `/login`
- `/devices`
- `/devices/add`
- `/devices/setup-finishing`
- `/devices/{device_id}`
- `/devices/{device_id}/summary.json`
- `/setup/status.json`
- web form posts for add-device and command actions

Current file roots:

- `platform/backend/app/web/routes.py`
- `platform/backend/app/web/templates/`
- `platform/backend/app/web/static/`

## Current auth coupling

The browser app currently depends on backend session behavior:

- web pages use `request.session["user_id"]`
- `/auth/login` and `/auth/callback` are browser redirect flows
- `/auth/logout` clears the backend session

This is fine for Stage 1, but it is not the final auth model for standalone web and mobile clients.

## Current dashboard coupling

The current dashboard view depends on backend-side assembly logic in web routes.

Examples:

- device overview cards are assembled on the server
- device detail page data is assembled on the server
- setup-finishing readiness is decided on the server

This means the standalone web frontend will need API-facing equivalents for:

- device summary
- latest reading summary
- latest image summary
- command activity summary
- setup-finishing status

## Current provisioning and onboarding coupling

Provisioning is partly API-backed and partly web-route-backed:

- device setup code creation is triggered through backend-rendered web flow
- setup-finishing polling is currently exposed through backend web routes
- device registration itself already relies on backend API endpoints

For Stage 2, the browser onboarding flow should move to standalone frontend screens that talk to backend APIs only.

## Separation implications

### Safe to leave in backend long term

- models
- schemas
- services
- device registration
- readings ingest
- image ingest
- command APIs
- device-node APIs
- health endpoints

### Must be replaced before backend becomes API-only

- login page
- devices list page
- device dashboard page
- setup-finishing page
- add-device page
- summary JSON currently living under web routes

## Migration rule

Do not remove backend-rendered routes until the standalone `platform/web` implementation fully replaces their user-facing behavior.
