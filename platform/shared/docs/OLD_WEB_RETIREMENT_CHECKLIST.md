# Old Web Retirement Checklist

This checklist tracks the backend-rendered web surface that still exists under:

- [platform/backend/app/web/routes.py](/Users/gary/plantOS/platform/backend/app/web/routes.py)
- [platform/backend/app/web/templates](/Users/gary/plantOS/platform/backend/app/web/templates)

The goal is to retire the old backend-rendered web safely later, without deleting anything prematurely.

## Status key

- `Covered`: `platform/web` has a clear equivalent flow today
- `Partial`: `platform/web` has part of the flow, but not enough to remove the old route safely
- `Missing`: no real replacement yet

## Page routes

| Old route | Template | Current purpose | `platform/web` equivalent | Coverage | Safe to remove later? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET /` | `index.html` | Landing page / signed-in redirect surface | None | Missing | No | New standalone web currently starts at app login and devices, not a public landing page. |
| `GET /login` | `login.html` | Google sign-in page for backend-rendered web | `/login` | Partial | No | New web has dev-only standalone login, not production Google sign-in parity yet. |
| `GET /devices` | `devices.html` | Device list, card overview, remove-device entry point, add-device entry point | `/devices` | Partial | No | New web covers list browsing, refresh, and status, but not device removal or full setup handoff yet. |
| `GET /devices/add` | `add_device.html` | Guided add-device setup flow, SN setup-code request, Wi-Fi handoff copy | None | Missing | No | This is still old-web-only. |
| `GET /devices/setup-finishing` | `setup_finishing.html` | Setup polling / ready-state redirect during onboarding | None | Missing | No | Still depends on backend flow and transitional setup JSON. |
| `GET /devices/{device_id}` | `device_detail.html` | Detailed dashboard, images, controls, component summary, activity | `/devices/:deviceId` | Partial | No | New web covers the main dashboard and controls, but not full parity for recent images grid, command activity, and trend charts. |

## Transitional JSON routes still under backend web

These are not final API routes, but they still power the old browser experience.

| Old route | Current purpose | Replacement status | Safe to remove later? | Notes |
| --- | --- | --- | --- | --- |
| `GET /devices/{device_id}/summary.json` | Old dashboard live-refresh payload | Partial | No | New web uses real `/api/devices/{id}/summary`, but old template still depends on this route. |
| `GET /setup/status.json` | Old setup-finishing polling payload | Missing | No | No standalone replacement yet. |

## Old form/action routes

These are tied to backend-rendered forms and should stay until the old templates are fully retired or replaced.

| Old route | Current purpose | Replacement status | Safe to remove later? | Notes |
| --- | --- | --- | --- | --- |
| `POST /devices` | Old web create-device form | Missing | No | Standalone web does not yet own add-device creation flow. |
| `POST /devices/setup-code` | Old web setup-code / serial-number handoff | Missing | No | Still required by the old add-device flow. |
| `POST /devices/{device_id}/delete` | Old web remove-device action | Missing | No | Standalone web does not yet expose device removal. |
| `POST /devices/{device_id}/commands` | Old web generic command form submit | Partial | No | Standalone web uses API wrapper endpoints for light/pump, but the old template still posts here. |

## Safe-removal summary

As of this checkpoint:

- No old backend-rendered route is safe to remove yet.
- The closest candidates for eventual retirement are:
  - `GET /devices`
  - `GET /devices/{device_id}`
  - `GET /login`
- But even those are only `Partial`, not `Covered`, because:
  - standalone web still uses dev-only auth
  - add-device and setup-finishing still live only in old web
  - the old dashboard still has features not yet mirrored in standalone web

## Remaining gaps before retirement can begin

1. Production-ready standalone auth that replaces old Google-sign-in web entry.
2. Standalone add-device flow in `platform/web`.
3. Standalone setup-finishing flow in `platform/web`.
4. Standalone remove-device flow in `platform/web`.
5. Feature parity decision for:
   - recent image gallery
   - command activity panel
   - trend charts / range picker
6. Decision on whether transitional JSON routes:
   - `/devices/{device_id}/summary.json`
   - `/setup/status.json`
   should be reimplemented as API-first endpoints or retired with the old pages.

## Current recommendation

Keep the old backend-rendered web in place for now.

Use this checklist as the gate before deleting anything:

- a route should only move to `Safe to remove later = Yes` after its standalone replacement works in local verification and no old template still depends on it.
