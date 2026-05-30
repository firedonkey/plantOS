# PlantLab Local ESP32 OTA and Image Upload Validation Report

Date: 2026-05-29

Scope: Reliability Validation Phase 2 against the local Docker backend using one real ESP32-S3 master node and one camera node.

Last updated: 2026-05-30 after Stage 8 local soak.

## Environment

- Backend: local Docker stack at `http://localhost:8000`
- Master hardware ID: `pl-esp32-64e0a80af6e8`
- Camera hardware ID: `pl-cam-1c1df816a398`
- Device ID: `8`
- Master firmware tested:
  - initial flashed build: `0.1.3`
  - OTA release 1: `0.1.4`
  - OTA release 2: `0.1.5`
- Camera firmware observed: `0.1.4`
  - REL-LOCAL-009 fix was delivered by camera OTA to `0.1.5`.

## Stage Results

| Stage | Status | Evidence |
| --- | --- | --- |
| 1. Firmware build validation | Pass | `esp32-local` and `camera-platform-test` PlatformIO builds passed. |
| 2. Initial device registration | Pass | Master and camera nodes were online in `device_hardware_ids`. |
| 3. Heartbeat validation | Pass | 15-minute window: master 90 heartbeats, camera 21 heartbeats, master RSSI -58 to -47 dBm, time sync `synchronized`. |
| 4. Command validation | Pass after fixes | `REQUEST_DIAGNOSTICS`, `SET_LIGHT_BRIGHTNESS`, `CAPTURE_IMAGE`, and `REBOOT` all completed with command lifecycle events. |
| 5. Image upload validation | Pass | Capture command uploaded real camera JPEGs; latest served image was 1600x1200 JPEG. Image capture/upload events were emitted. |
| 6. OTA validation | Pass after fixes | OTA `0.1.4 -> 0.1.5` completed with OTA lifecycle events and no premature `COMMAND_TIMED_OUT`. |
| 7. Reboot recovery | Pass with known diagnostics artifact | Contract `REBOOT` command completed. Physical power-cycle was confirmed by master uptime reset from `1031` to `10` seconds at `2026-05-29T14:49:07Z`; post-cycle diagnostics and capture commands completed. REL-LOCAL-009 was traced to stale camera firmware diagnostics. |
| 8. Short soak | Pass | Minimum 2-hour local soak completed from `2026-05-30T03:56:54Z` through `2026-05-30T05:59:56Z`; no warning events, no backend errors, no unexpected resets, commands and image uploads passed. |

## Command Validation

Validated commands:

- `REQUEST_DIAGNOSTICS`: command `225`, completed.
- `SET_LIGHT_BRIGHTNESS`: command `226`, completed, light intensity `42%`.
- `CAPTURE_IMAGE`: command `227`, completed, image uploaded.
- `REBOOT`: command `228` and reboot validation command `231`, completed.

Events observed:

- `COMMAND_QUEUED`
- `COMMAND_POLLED`
- `COMMAND_SENT`
- `COMMAND_ACKED`
- `COMMAND_IN_PROGRESS`
- `COMMAND_COMPLETED`

## Image Upload Validation

Evidence:

- Latest image ID: `6951`
- Source node: `pl-cam-1c1df816a398`
- Served content: JPEG, 1600x1200, approximately 62 KB
- Image events observed:
  - `IMAGE_CAPTURE_STARTED`
  - `IMAGE_UPLOAD_STARTED`
  - `IMAGE_CAPTURED`
  - `IMAGE_UPLOADED`

The image gallery endpoint returned recent real camera images, and the timelapse endpoint returned real frames.

## OTA Validation

First OTA:

- Release: `local-master-0.1.4-20260529`
- Result: firmware installed and eventually completed, but backend emitted a premature `COMMAND_TIMED_OUT`.
- Root cause: OTA commands used the default 20-second timeout.

Retest OTA:

- Release: `local-master-0.1.5-20260529`
- Result: pass.
- Command: `230`
- Final firmware version: `0.1.5`
- Final node OTA state: `idle`
- OTA success timestamp: `2026-05-29T14:30:54Z`

Events observed:

- `OTA_STARTED`
- `OTA_PREPARING`
- `OTA_DOWNLOADING`
- `OTA_VALIDATING`
- `OTA_INSTALLING`
- `OTA_REBOOTING`
- `OTA_SUCCESS`
- `OTA_STATE_CHANGED`
- `COMMAND_COMPLETED`

No `COMMAND_TIMED_OUT` event was emitted for the successful retest command.

## Reboot and Physical Power-Cycle Validation

Software reboot:

- Command: `231`
- Result: completed with message `device reboot scheduled`.
- Evidence: master heartbeat resumed with uptime reset to `10` seconds.

Physical power-cycle:

- Master hardware ID: `pl-esp32-64e0a80af6e8`
- Firmware version after reconnect: `0.1.5`
- Pre-cycle heartbeat: `2026-05-29T14:48:45Z`, uptime `1031`, RSSI `-50`, `time_sync_status=synchronized`, `last_ntp_sync_at=2026-05-29T14:34:19Z`
- Post-cycle heartbeat: `2026-05-29T14:49:07Z`, uptime `10`, RSSI `-50`, `time_sync_status=synchronizing`
- Follow-up heartbeat: `2026-05-29T14:49:17Z`, uptime `20`, `time_sync_status=synchronized`, `last_ntp_sync_at=2026-05-29T14:49:08Z`
- Timeline behavior: `HEARTBEAT_RECEIVED` resumed after the power interruption. No `DEVICE_OFFLINE` or `DEVICE_ONLINE` event was emitted, likely because the interruption was shorter than the backend offline threshold.

Post-power-cycle command checks:

- `REQUEST_DIAGNOSTICS`: command `232`, completed at `2026-05-29T15:04:17Z` with message `diagnostics heartbeat sent`.
- `CAPTURE_IMAGE`: command `233`, completed at `2026-05-29T15:04:20Z` with message `camera uploaded a new image`.
- Latest captured image: `6957`, source `pl-cam-1c1df816a398`, served as a valid 1600x1200 JPEG.

Post-power-cycle heartbeat watch:

- Window: `2026-05-29T15:04:33Z` through `2026-05-29T15:19:37Z`
- Master heartbeats: `90`
- Camera heartbeats: `20`
- Master uptime advanced from `930` to `1834` seconds during the watch.
- Camera runtime state from master heartbeat remained `online`.
- Warning found: camera emitted one `upload_failure` warning and one `last_error` event at `2026-05-29T15:15:12Z`, followed by repeated camera `DIAGNOSTICS_RECEIVED` warnings. This is tracked as `REL-LOCAL-009`.

REL-LOCAL-009 follow-up:

- Root cause: camera firmware kept reporting upload-related `last_error_code` after later successful heartbeat/image uploads, causing backend diagnostics to remain warning.
- Evidence of recovery: scheduled images `6958` and `6959` succeeded after the original warning; manual retest commands `234`, `235`, and `236` uploaded images `6960`, `6961`, and `6962`.
- Current health: camera remained online, RSSI was approximately `-52 dBm`, and `last_camera_image_upload_at` updated to `2026-05-30T02:49:47Z`.
- Fix: camera firmware now clears `heartbeat_upload_failed` after successful heartbeat and clears `image_upload_failed` after successful image upload while preserving cumulative error counters.
- OTA validation: camera release `local-camera-0.1.5-rel-local-009` updated the camera from `0.1.4` to `0.1.5` and emitted `OTA_SUCCESS` at `2026-05-30T03:29:44Z`.
- OTA telemetry caveat: the camera OTA emitted `OTA_AVAILABLE`, `OTA_STARTED`, `OTA_DOWNLOADING`, `OTA_INSTALLING`, and `OTA_SUCCESS`, but did not emit `OTA_PREPARING`, `OTA_VALIDATING`, or `OTA_REBOOTING`. This is tracked separately as `REL-LOCAL-010`.
- Retest after OTA: capture commands `237`, `238`, and `239` completed and uploaded images `6965`, `6966`, and `6967`.
- Diagnostics recovery: no camera warning or non-info events were observed after `OTA_SUCCESS`.

## Stage 8 Local Soak

Window:

- Start: `2026-05-30T03:56:54Z`
- End: `2026-05-30T05:59:56Z`
- Duration: approximately 2 hours 3 minutes

Node state:

- Master `pl-esp32-64e0a80af6e8`: firmware `0.1.5`, OTA state `idle`
- Camera `pl-cam-1c1df816a398`: firmware `0.1.5`, OTA state `idle`

Heartbeat and uptime:

| Node | Heartbeats | Max gap | Start uptime | End uptime | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Master | 733 | 21.7s | 1769s | 9145s | Pass |
| Camera | 164 | 53.8s | 1710s | 9046s | Pass |

Image upload:

- Images uploaded during soak: 4
- Image IDs: `6968` through `6971`
- First capture: `2026-05-30T03:57:19Z`
- Last capture: `2026-05-30T05:59:14Z`
- Upload failures observed: 0

Commands tested:

| Command ID | Command | Result |
| ---: | --- | --- |
| 240 | `REQUEST_DIAGNOSTICS` | Completed |
| 241 | `CAPTURE_IMAGE` | Completed; image uploaded |
| 242 | `SET_LIGHT_BRIGHTNESS` to 55% | Completed |
| 243 | `REQUEST_DIAGNOSTICS` | Completed |
| 244 | `SET_LIGHT_BRIGHTNESS` to 60% | Completed |
| 245 | `CAPTURE_IMAGE` | Completed; image uploaded |

Event and diagnostics health:

- Device events during soak: 926
- Event severities: 926 `info`, 0 warnings/errors
- Non-info camera events after REL-LOCAL-009 OTA: 0
- Event volume was stable; no event storm was observed.

Backend and database health:

- Platform backend errors during soak: 0
- Product PostgreSQL errors during soak: 0
- Monitoring query errors: 1, caused by querying a non-existent `free_heap_bytes` column; not a product/runtime failure.

Memory observations:

- `free_heap_bytes` is not currently stored in `device_diagnostic_snapshots`.
- No heap trend could be produced from the current backend schema during this soak.

## Fixes Applied

- Added backend contract command adapter/API support for:
  - `REQUEST_DIAGNOSTICS`
  - `REBOOT`
- Added firmware execution support for contract `REBOOT` using the existing scheduled restart mechanism.
- Widened `commands.value` from 120 to 2000 characters so `START_OTA` command params can carry checksum, release id, hardware model, and artifact size.
- Added a lightweight local migration to widen existing local database columns.
- Increased OTA command timeout to 1800 seconds to cover install, reboot, and delayed success reporting.
- Bumped master firmware version to `0.1.5` after OTA validation.
- Fixed stale camera upload-related diagnostic errors after recovered heartbeat/image upload.

## Blockers

- None for local Phase 2.
- Accepted known issue: `REL-LOCAL-010` camera OTA phase telemetry does not block Stage 8 or GCP simulator validation.

## Final Validation Commands

- `.venv/bin/pytest platform/backend/tests/contracts/test_contract_command_polling.py -q` -> `11 passed`
- `.venv/bin/pytest platform/backend/tests/test_commands.py platform/backend/tests/contracts/test_contract_command_polling.py platform/backend/tests/test_firmware_ota_api.py -q` -> `32 passed`
- `.venv/bin/pytest platform/backend/tests -q` -> `270 passed`
- `.venv/bin/pytest tools/simulator -q` -> `11 passed`
- `.venv/bin/pio run -d device/esp32 -e esp32-local` -> passed
- `.venv/bin/pio run -d device/esp32 -e camera-platform-test` -> passed
- `git diff --check` -> passed

Final observed node state:

- Master `pl-esp32-64e0a80af6e8`: online, firmware `0.1.5`, OTA state `idle`
- Camera `pl-cam-1c1df816a398`: online, firmware `0.1.5`, OTA state `idle`

## Recommendation

Safe to proceed to Phase 3: GCP Deployment + Simulator Stress Validation.

Carry forward `REL-LOCAL-010` as an accepted telemetry completeness issue unless camera OTA phase visibility is required before cloud validation.
