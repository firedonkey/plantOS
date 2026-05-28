# PlantLab Public Demo Page

## Purpose

The public demo page at `/demo` gives visitors a no-auth preview of the
PlantLab product experience. It uses static frontend data only. It does not
call backend APIs, require a device token, or depend on the simulator process.

## Demo Images

The current demo uses 34 repo-local mockup growth frames stored in:

- `platform/web/src/assets/demo/growth/frame_0001.jpg` through `frame_0034.jpg`
- `platform/web/src/assets/demo/CREDITS.md`

Do not store public demo assets under deprecated hardware folders. The web demo
should remain self-contained under
`platform/web/src/assets/demo` so it is independent of obsolete hardware
experiments.

`CREDITS.md` records that these were copied from Gary's local mockup frame set.
The frontend imports only the repo-local copies and does not depend on the
absolute source path.

Before a public launch, confirm the frames are approved for marketing use or
replace them with final user-owned PlantLab growth captures.

The older rose placeholder images are retained in `platform/web/src/assets/demo`
for internal reference only. The public demo route no longer imports them.

## Replacement Plan

For launch-quality demo imagery, capture the same plant over time:

- a full same-angle sequence
- at least one clear starting frame
- enough intermediate frames to show slow growth
- a latest frame that feels meaningfully different from the start

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
- visible sample-data disclosure

This keeps the demo self-contained and safe for public browsing.

## Limitations

- Demo data is static and does not reflect a real backend device.
- Current images are mockup frames and should be approved or replaced before
  public launch.
- The `/demo` route is a frontend-only route and relies on SPA fallback support
  from the web host.
- The route intentionally avoids auth, backend APIs, simulator state, and device
  commands.
