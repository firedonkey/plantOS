# PlantLab Reliability Issues

This file tracks issues found during local reliability validation.

## REL-LOCAL-001: Simulator tests failed outside repo-root pytest discovery

- Scenario: Preflight simulator tests
- Severity: Medium
- Root cause: Pytest selected `tools/simulator` as the root and could not import the top-level `tools` package.
- Fix: Added root-level `pytest.ini` with `pythonpath = .`.
- Validation: `.venv/bin/pytest tools/simulator -q` passed with `11 passed`.

## REL-LOCAL-002: Backend tests asserted stale onboarding copy

- Scenario: Backend full test suite
- Severity: Medium
- Root cause: Recent onboarding UX copy changed, but `test_mobile_ble_wifi_networks.py` still asserted old source strings.
- Fix: Updated the assertions to match current mobile onboarding copy.
- Validation:
  - `.venv/bin/pytest platform/backend/tests/test_mobile_ble_wifi_networks.py -q` passed with `21 passed`.
  - `.venv/bin/pytest platform/backend/tests -q` passed with `265 passed`.

## REL-LOCAL-003: Simulator command validation was contaminated by a real ESP32

- Scenario: Stage 5 OTA validation
- Severity: Medium
- Root cause: The stress script auto-selected the first active device token. A physical ESP32 was also polling that device record and could consume queued commands.
- Fix: Added `CREATE_SIMULATOR_DEVICE=1` support to `scripts/stress/local_simulator_stress.sh` so simulator-only validation can create an isolated local device through the existing backend API.
- Validation: Stage 5 OTA success and failure were rerun on isolated simulator devices and passed.

## REL-LOCAL-004: OTA stress command bypassed COMMAND_QUEUED

- Scenario: Stage 5 OTA lifecycle validation
- Severity: Low
- Root cause: The stress script inserted OTA commands directly into the `commands` table, bypassing canonical `COMMAND_QUEUED` event creation.
- Fix: Changed stress OTA queuing to use the existing `/api/devices/{id}/commands` API.
- Validation: Isolated OTA success run produced `COMMAND_QUEUED`, `COMMAND_SENT`, `COMMAND_ACKED`, `COMMAND_COMPLETED`, and OTA lifecycle events.

## REL-LOCAL-005: Command and OTA timeline events were pruned under noisy diagnostics

- Scenario: Stage 5 OTA lifecycle validation
- Severity: High
- Root cause: Per-device diagnostic event retention was capped at 100. High-frequency heartbeat, diagnostics, and image events pruned command/OTA lifecycle events within minutes.
- Fix: Increased per-device diagnostic event retention cap to 1000 and added a regression test.
- Validation:
  - `.venv/bin/pytest platform/backend/tests/test_device_diagnostics_retention.py -q` passed.
  - Isolated OTA success run retained command and OTA lifecycle events after the stress window.
  - Isolated OTA failure run retained `COMMAND_FAILED` and `OTA_FAILED`.

## REL-LOCAL-006: Real firmware could not receive required diagnostics and reboot validation commands

- Scenario: Phase 2 Stage 4 real-device command validation
- Severity: High
- Root cause: Shared contract constants included `REQUEST_DIAGNOSTICS` and `REBOOT`, and firmware parsed them, but backend command creation/adaptation did not expose diagnostics/reboot commands. Firmware also explicitly rejected `REBOOT`.
- Fix: Added backend command target/action support for `diagnostics:request` and `system:reboot`, mapped both to typed command envelopes, and wired firmware `REBOOT` to the existing scheduled restart path.
- Validation:
  - `.venv/bin/pytest platform/backend/tests/contracts/test_contract_command_polling.py -q` passed.
  - Real commands `225` through `228` completed on the ESP32 with lifecycle events.

## REL-LOCAL-007: START_OTA command payload exceeded command value length

- Scenario: Phase 2 Stage 6 real OTA validation
- Severity: High
- Root cause: `commands.value` was limited to 120 characters, which is too small for a contract `START_OTA` payload containing release id, artifact URL, SHA-256 checksum, artifact size, channel, and hardware model.
- Fix: Widened `commands.value` to 2000 characters in the model/schema and added a lightweight local migration for existing dev databases.
- Validation:
  - Local Postgres column `commands.value` reports `character_maximum_length = 2000`.
  - Full checksum-bearing `START_OTA` commands queued successfully after the fix.

## REL-LOCAL-008: Real OTA command timed out before post-reboot success report

- Scenario: Phase 2 Stage 6 real OTA validation
- Severity: High
- Root cause: OTA commands used the default 20-second stale-command timeout. Firmware intentionally reports OTA success after reboot and after its initial OTA service delay, so the command could time out while the update was otherwise healthy.
- Fix: Added an OTA-specific command timeout of 1800 seconds.
- Validation:
  - `.venv/bin/pytest platform/backend/tests/test_commands.py platform/backend/tests/contracts/test_contract_command_polling.py platform/backend/tests/test_firmware_ota_api.py -q` passed with `32 passed`.
  - Retest OTA from `0.1.4` to `0.1.5` completed as command `230` with no `COMMAND_TIMED_OUT` event.

## REL-LOCAL-009: Camera warning diagnostics persisted after recovered heartbeat/upload

- Scenario: Phase 2 Stage 7 physical power-cycle continuity watch
- Severity: Medium
- Classification: B - minor diagnostics bug / stale warning artifact.
- Root cause: Camera firmware recorded upload-related diagnostic errors in `g_last_diagnostic_error_code` but did not clear them after a later successful heartbeat or image upload. The backend correctly continued to mark diagnostics as warning whenever the camera heartbeat still included `last_error_code`.
- Responsibility: Firmware diagnostics lifecycle. Backend image storage, authentication, and event ingestion remained healthy in the available logs and database evidence.
- Fix: Added camera firmware recovery clearing for upload-related last-error codes:
  - successful heartbeat clears `heartbeat_upload_failed`
  - successful image upload clears `image_upload_failed`
  - cumulative upload failure counters are preserved
- Validation:
  - Physical power-cycle was confirmed by master uptime reset from `1031` to `10` seconds at `2026-05-29T14:49:07Z`.
  - Post-power-cycle diagnostics command `232` completed.
  - Post-power-cycle capture command `233` completed and uploaded a valid 1600x1200 JPEG.
  - Both master and camera remained online during the 15-minute watch.
  - Scheduled images `6958` and `6959` uploaded successfully after the original warning.
  - Manual retest commands `234`, `235`, and `236` completed and uploaded images `6960`, `6961`, and `6962`.
  - The current camera snapshot updated `last_camera_image_upload_at` to `2026-05-30T02:49:47Z`, confirming image uploads were still healthy.
  - `.venv/bin/pio run -d device/esp32 -e camera-platform-test` passed after the firmware fix.
- OTA validation:
  - Published camera-only local release `local-camera-0.1.5-rel-local-009`.
  - Firmware artifact: `device/esp32/.pio/build/camera-platform-test/firmware.bin`.
  - SHA-256: `764db4c9ba3c45ef3079c28225521ac1c12702ba381006e218ee5a3f8edf3b6b`.
  - Camera picked up the manifest after power cycle, downloaded the artifact, installed it, rebooted, and reported `OTA_SUCCESS` at `2026-05-30T03:29:44Z`.
  - Camera firmware changed from `0.1.4` to `0.1.5`.
  - Retest capture commands `237`, `238`, and `239` completed and uploaded images `6965`, `6966`, and `6967`.
  - No warning or non-info camera events were observed after `OTA_SUCCESS`.
- Resolution: Resolved. REL-LOCAL-009 no longer blocks Stage 8 local soak.

## REL-LOCAL-010: Camera OTA omitted some intermediate phase events

- Scenario: Camera OTA validation for REL-LOCAL-009 firmware delivery.
- Severity: Medium
- Classification: OTA telemetry completeness gap.
- Root cause: Unknown. Firmware source calls `reportStatus()` for `preparing`, `downloading`, `validating`, `installing`, and `rebooting`, but the backend only received four OTA status posts during the camera OTA.
- Evidence:
  - Release `local-camera-0.1.5-rel-local-009` was published for camera `pl-cam-1c1df816a398`.
  - Observed timeline events: `OTA_AVAILABLE`, `OTA_STARTED`, `OTA_DOWNLOADING`, `OTA_INSTALLING`, `OTA_SUCCESS`.
  - Missing expected phase events: `OTA_PREPARING`, `OTA_VALIDATING`, `OTA_REBOOTING`.
  - Functional OTA succeeded; camera firmware updated from `0.1.4` to `0.1.5`.
- Fix: Not applied. Needs serial-log-backed investigation before changing OTA status retry/timing behavior.
- Validation:
  - Backend tests passed.
  - Camera firmware build passed.
  - Post-OTA image uploads succeeded.
- Recommendation: Accepted for Stage 8 local soak and GCP simulator validation. Does not block REL-LOCAL-009 diagnostics recovery, but should be resolved before treating camera OTA telemetry as fully validated.

## REL-GCP-001: Cloud image APIs fell back to authenticated proxy URLs

- Scenario: Phase 3 Gate 5 cloud smoke validation.
- Severity: High
- Classification: Cloud storage signed URL configuration bug.
- Root cause: Cloud Run used metadata-server compute credentials without a private key. The first GCS signed URL path correctly fell back to IAM signing, but the fallback used unscoped credentials and then the metadata credential's `service_account_email` value of `default`. IAM `signBlob` requires an access token with the `cloud-platform` scope and the actual service account email.
- Impact: Image metadata APIs still returned HTTP 200, but `content_url` fell back to authenticated `/api/images/{id}/content` proxy URLs. This risked broken public web image rendering and produced repeated Cloud Run ERROR logs.
- Fix: Updated backend image storage signing to:
  - force `cloud-platform` scoping when credentials support `with_scopes`
  - resolve the real Cloud Run service account email from the metadata server when credentials report `default`
  - keep the authenticated proxy fallback for any future signing failure
- Validation:
  - `.venv/bin/pytest platform/backend/tests/test_images.py -q` passed with `23 passed`.
  - `.venv/bin/pytest platform/backend/tests -q` passed with `272 passed`.
  - Deployed backend hotfix revision `plantlab-api-00062-yoh`.
  - Cloud image API returned signed `https://storage.googleapis.com/...X-Goog-Algorithm=GOOG4-RSA-SHA256...` URLs for images `1253`, `1254`, and `1255`.
  - Cloud Run ERROR log check for `plantlab-api-00062-yoh` returned no errors after retest.
- Resolution: Resolved during Gate 5. Continue cloud validation.

## REL-GCP-002: Cloud OTA command payload exceeded commands.value length

- Scenario: Phase 3 Gate 9 simulator OTA validation.
- Severity: High
- Classification: Cloud database migration gap.
- Root cause: The application model and local schema used `commands.value` length 2000, but GCP still had `commands.value` as `varchar(120)`. Queueing a contract `START_OTA` payload triggered `psycopg.errors.StringDataRightTruncation` and returned HTTP 500.
- Impact: Cloud `START_OTA` commands with realistic payloads could not be queued.
- Fix:
  - Added Alembic migration `20260530_0013_expand_command_value.py`.
  - Took a Cloud SQL backup.
  - Ran the GCP migration job successfully.
  - Deployed matching backend revision `plantlab-api-00064-qib`.
- Validation:
  - Local Alembic head reports `20260530_0013`.
  - `.venv/bin/pytest platform/backend/tests -q` passed with `272 passed`.
  - GCP schema check reports `alembic_version=20260530_0013`.
  - GCP schema check reports `commands_value_length=2000`.
  - Retried `START_OTA`; command `236` queued, was sent, acked, moved in progress, completed, and produced OTA status events through `OTA_SUCCESS`.
- Resolution: Resolved during Gate 9. Continue cloud validation.

## REL-GCP-HW-001: Real ESP32 and camera were not reporting to GCP at Phase 4 start

- Scenario: Phase 4 Gate 2 real hardware connection validation.
- Severity: High
- Classification: Validation blocker / runtime provisioning mismatch.
- Root cause: The real hardware records exist in GCP, but both nodes had stale `last_seen_at` timestamps and older firmware versions. The local firmware fallback config also points to the local backend, so flashing without reprovisioning or updating runtime credentials would not validate GCP connectivity.
- Evidence:
  - Master `pl-esp32-64e0a80af6e8` in GCP: firmware `0.1.3`, last seen `2026-05-28T13:48:06Z`.
  - Camera `pl-cam-1c1df816a398` in GCP: firmware `0.1.4`, last seen `2026-05-29T02:16:52Z`.
  - Current firmware constants build as `0.1.5`.
  - Local `platform_secrets.h` fallback `PLANTLAB_PLATFORM_URL` points to the local backend.
  - Connected serial ports were detected, but the camera port reported as USB BillBoard rather than a confirmed XIAO ESP32S3 serial interface.
- Fix: Not applied. Requires operator decision to reprovision to GCP or approve NVS erase plus cloud runtime configuration.
- Validation:
  - Firmware builds passed for `esp32-local`, `camera-platform-test`, and `esp32-gcp`.
  - GCP database lookup confirmed no current real hardware heartbeat.
- Retest:
  - Repeated Phase 4 Gate 1 builds at `2026-05-30T16:35:35Z`; `esp32-local`, `camera-platform-test`, and `esp32-gcp` all passed.
  - GCP records remained unchanged: master last seen `2026-05-28T13:48:06Z`, camera last seen `2026-05-29T02:16:52Z`.
  - No current heartbeat or diagnostics events were observed for either node.
- Recommendation: Block Phase 4 at Gate 2. Reprovision/flash real hardware for GCP, then rerun Gate 2 before heartbeat, image upload, command, OTA, or soak validation.
- Recovery:
  - Confirmed the master was physically connected on `/dev/cu.usbmodem1301` and running firmware `0.1.5`, but its persisted runtime config still pointed to the local backend:
    - `platform_id=8`
    - `platform=http://192.168.0.55:8000`
    - provisioning env `local`
  - Seeded the master NVS runtime config with the existing GCP device `34` provisioning values and backend URL `https://api.marspotatolab.com`.
  - Reflashed normal `esp32-gcp` firmware after seeding runtime config.
  - Did not change firmware behavior, backend APIs, onboarding, OTA, or simulator behavior.
- Retest:
  - Master boot logs confirmed:
    - firmware `0.1.5 (1005)`
    - provisioning env `gcp`
    - platform base URL `https://api.marspotatolab.com`
    - platform device id `34`
  - GCP hardware records at `2026-05-30T17:00:04Z`:
    - master `pl-esp32-64e0a80af6e8`: firmware `0.1.5`, online, last seen `2026-05-30T16:59:50.751118Z`
    - camera `pl-cam-1c1df816a398`: firmware `0.1.5`, online, last seen `2026-05-30T16:59:39.603469Z`
  - Previous 15 minutes of GCP heartbeat events:
    - master: `53`
    - camera: `11`
  - Command `237` (`REQUEST_DIAGNOSTICS`) completed.
  - Command `238` (`CAPTURE_IMAGE`) completed and uploaded image `1488`.
  - GCS object exists at `gs://plantlab-images-garylu/device-34/20260530_165821_869412_8ce26b95f6364e9aa9b652edc6424877.jpg`, size `55742` bytes, content type `image/jpeg`.
- Resolution: Resolved for the original GCP hardware-reporting blocker. Gate 2 can continue after acknowledging the separate diagnostic snapshot freshness caveat.

## REL-GCP-HW-002: Contract heartbeat runtime state does not refresh legacy diagnostic snapshots

- Scenario: Phase 4 Gate 2 recovery diagnostics check.
- Severity: Medium
- Classification: Telemetry freshness gap / validation caveat.
- Root cause: Current firmware sends rich contract heartbeat envelopes, and the backend records those runtime fields in canonical `HEARTBEAT_RECEIVED` timeline data. The older `device_diagnostic_snapshots` table is refreshed from legacy heartbeat diagnostics or contract diagnostics envelopes, so it remained stale after contract-heartbeat-only recovery.
- Evidence:
  - Latest master canonical heartbeat included firmware `0.1.5`, uptime, RSSI, free heap, OTA status, camera-node status, NTP sync state, and runtime state.
  - Latest camera canonical heartbeat included firmware `0.1.5`, uptime and RSSI.
  - Legacy diagnostic snapshots remained stale:
    - master snapshot firmware `0.1.3`, reported `2026-05-28T06:56:16Z`
    - camera snapshot firmware `0.1.4`, reported `2026-05-29T02:16:52Z`
- Impact:
  - GCP timeline/runtime evidence is current.
  - Any dashboard/API view that still relies on `device_diagnostic_snapshots` may show stale diagnostics for contract-heartbeat-only firmware.
- Fix:
  - Contract heartbeat ingestion now derives a lightweight `HardwareDiagnosticsCreate` snapshot from heartbeat payload fields:
    - `uptime_seconds`
    - `wifi_rssi_dbm`
    - `runtime.provisioning_status`
    - `runtime.last_command_id`
    - `runtime.last_command_status`
  - The derived snapshot refreshes `device_diagnostic_snapshots` but does not emit `DIAGNOSTICS_RECEIVED` for every heartbeat, avoiding additional timeline noise.
  - Legacy heartbeat diagnostics still emit `DIAGNOSTICS_RECEIVED` as before.
- Validation:
  - Focused contract heartbeat test confirms the snapshot is refreshed from actuator/runtime heartbeat payloads.
  - Focused legacy heartbeat diagnostics test confirms existing diagnostic snapshot behavior still works.
  - Deployed backend revision `plantlab-api-00066-wuf`.
  - Production snapshot validation after 2-3 heartbeats confirmed:
    - master snapshot updated to firmware `0.1.5`, RSSI `-51`, uptime `5726`, `provisioning_state=NORMAL`, `last_command_id=238`, `last_command_status=completed`, `updated_at=2026-05-30T18:26:32.347699Z`
    - camera snapshot updated to firmware `0.1.5`, RSSI `-52`, uptime `5715`, `updated_at=2026-05-30T18:26:39.484857Z`
- Resolution: Resolved in production.

## REL-GCP-HW-003: Camera heartbeat remains time-unsynchronized during Gate 3

- Scenario: Phase 4 Gate 3 heartbeat and diagnostics observation.
- Severity: Medium
- Classification: Firmware telemetry completeness / timestamp readiness.
- Root cause: The master firmware initializes and services `time_sync_manager`, but the camera platform firmware entrypoint did not call `plantlab::time_sync::begin()` or `plantlab::time_sync::service()`. Camera heartbeat envelopes therefore continued reporting `runtime.time_sync_status=unsynchronized`.
- Evidence:
  - Gate 3 observation window: `2026-05-30T18:26:56Z` to `2026-05-30T18:41:56Z`.
  - Latest camera heartbeat runtime values repeatedly showed `{"time_sync_status": "unsynchronized"}`.
  - Master heartbeat runtime showed `time_sync_status=synchronized` and `last_ntp_sync_at=2026-05-30T16:46:59Z`.
  - Source check found NTP setup/service calls in `device/esp32/src/main.cpp`, but not in `device/esp32/src/tests/camera_platform_test_main.cpp`.
- Impact:
  - Backend receives and orders camera events using server receive time, so heartbeat/timeline ingestion remains stable.
  - Camera-originated contract timestamps may remain fallback/unsynchronized until camera firmware wires in NTP sync.
- Fix:
  - Added camera firmware NTP startup/service wiring in `device/esp32/src/tests/camera_platform_test_main.cpp`.
  - Bumped camera firmware constants to `0.1.6 (1006)`.
  - Built `camera-platform-test` successfully.
  - Published GCP camera-only OTA release `camera-0.1.6-gcp` for `pl-cam-1c1df816a398`.
  - Artifact: `gs://plantlab-images-garylu/firmware/camera-0.1.6-gcp.bin`
  - SHA-256: `f7a2eb7319a8878c39a8d46b2eed276e259d38f54f96591d00765406c7671953`
- Retest:
  - Five-minute GCP poll after publishing still showed camera firmware `0.1.5` and `runtime.time_sync_status=unsynchronized`.
  - No camera OTA events were observed after release publication during that poll window.
  - Current visible USB devices do not expose the camera as an Espressif serial flash target; `/dev/cu.usbmodem1301` is the master and `/dev/cu.usbmodemSN234567892` reports as `USB BillBoard`.
- Resolution: Patch published but not installed. Full resolution requires camera power-cycle/reset to trigger the boot-time manifest check, waiting for the next scheduled manifest poll, or direct camera serial flashing.
- Recommendation: Keep Phase 4 Gate 3 blocked until the camera reports firmware `0.1.6` and `runtime.time_sync_status=synchronized` for a fresh 15-minute observation window.

## REL-GCP-HW-004: Camera OTA to 0.1.6 failed while writing artifact

- Scenario: Phase 4 Gate 3 camera NTP patch delivery after camera power-cycle.
- Severity: High
- Classification: Camera OTA install blocker.
- Evidence:
  - Camera requested the GCP manifest after power-cycle and received release `camera-0.1.6-gcp`.
  - Observed events:
    - `OTA_AVAILABLE` at `2026-05-30T19:04:59Z`
    - `OTA_STARTED` at `2026-05-30T19:05:02Z`
    - `OTA_PREPARING` at `2026-05-30T19:05:02Z`
    - `OTA_DOWNLOADING` at `2026-05-30T19:05:03Z`
    - `OTA_FAILED` at `2026-05-30T19:05:06Z`
  - Failure payload reported `failure_reason=download_failed` and `message=OTA artifact write failed`.
  - Hardware row after failure:
    - firmware remains `0.1.5`
    - `ota_status=failed`
    - `ota_target_version=0.1.6`
    - `ota_error=OTA artifact write failed`
  - Latest camera heartbeat after failure remained online with firmware `0.1.5` and `runtime.time_sync_status=unsynchronized`.
  - Cloud Run served `/api/hardware/ota/artifacts/camera-0.1.6-gcp` with HTTP 200.
  - Independent artifact fetch returned `1007888` bytes and SHA-256 `f7a2eb7319a8878c39a8d46b2eed276e259d38f54f96591d00765406c7671953`, matching the release metadata.
- Current assessment:
  - Backend artifact serving and release metadata appear correct.
  - Failure occurred on the camera firmware write path after download started.
  - Serial camera logs are needed to distinguish flash/partition/update-writer failure from a firmware OTA write-loop bug.
- Partition check:
  - Generated camera partition table uses two OTA app slots:
    - `app0`: `3264K`
    - `app1`: `3264K`
  - Current diagnostic camera firmware artifact size after added logging: `1009552` bytes.
  - Previous published `camera-0.1.6-gcp` artifact size: `1007888` bytes.
  - OTA slot size is therefore not the blocker.
- Fix/hardening:
  - Added firmware-side OTA diagnostics for the next serial-backed run:
    - `Update.begin()` requested size, result, `Update.getError()`, error string, and free heap
    - artifact HTTP status and content length
    - `Update.write()` requested length, returned length, cumulative bytes, `Update.getError()`, error string, and free heap
    - periodic OTA write progress/free-heap logs
  - Updated OTA failure reporting to prefer the lower-level `Update.write()` error when available instead of only reporting the generic download callback failure.
- Validation:
  - `camera-platform-test` build passed after adding OTA diagnostics.
- Remaining blocker:
  - These new logs are in firmware that is not yet running on the camera. The current camera `0.1.5` updater cannot emit them for the already-observed failure.
  - Current visible USB devices still do not expose the camera as an Espressif serial target; serial capture/direct flash requires connecting the camera board as a proper ESP32-S3 serial device.
- Recommendation: Do not rerun Gate 3 or proceed to image/command validation until the camera is either direct-flashed with the patched firmware or a serial-backed OTA attempt captures the detailed write failure.
