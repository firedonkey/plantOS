# PlantLab Public Demo Page

## Purpose

The public demo page at `/demo` gives visitors a no-auth preview of the
PlantLab product experience. It uses static frontend data only. It does not
call backend APIs, require a device token, or depend on the simulator process.

## Demo Images

The current demo uses existing repo-local rose mock images copied into:

- `platform/web/src/assets/demo/rose-01-seedling.jpg`
- `platform/web/src/assets/demo/rose-02-young-leaves.jpg`
- `platform/web/src/assets/demo/rose-03-bud.jpg`
- `platform/web/src/assets/demo/rose-04-bloom.jpg`
- `platform/web/src/assets/demo/rose-05-bloom.jpg`
- `platform/web/src/assets/demo/CREDITS.md`

Original source files live under:

- `device/raspberry_pi/dashboard/static/mock/`

The copied `CREDITS.md` includes the source URLs already present in the repo.
These images are acceptable for local/product-demo development because they are
existing project assets with source attribution. Before a public launch, replace
them with user-owned PlantLab growth photos or verify the exact license for each
source image.

## Replacement Plan

For launch-quality demo imagery, capture the same plant over time:

- day 1
- day 3
- day 7
- day 14
- today/latest capture

Recommended capture guidance:

- use the same PlantLab camera angle for every frame
- keep indoor lighting realistic
- include close-up leaf detail
- avoid AI-generated or cartoon-like images
- keep filenames stable if the demo data imports them directly

## Static Demo Data

The page currently includes:

- demo device name
- plant name
- device health
- Wi-Fi RSSI
- camera node status
- grow-light brightness
- latest capture
- growth timeline
- sample sensor readings
- recent activity events
- OTA/update readiness note

This keeps the demo self-contained and safe for public browsing.

## Limitations

- Demo data is static and does not reflect a real backend device.
- Current images are not a verified same-plant growth sequence.
- The `/demo` route is a frontend-only route and relies on SPA fallback support
  from the web host.
- The route intentionally avoids auth, backend APIs, simulator state, and device
  commands.
