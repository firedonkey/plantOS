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
