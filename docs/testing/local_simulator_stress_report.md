# PlantLab Local Simulator Stress Report

Date: 2026-05-29

Scope: Reliability Validation Phase 1, local simulator stress against the local Docker backend.

## Environment

- Backend: `http://localhost:8000`
- Docker services: `plantlab-local-platform`, `plantlab-local-postgres`
- Simulator: `tools/simulator/simulator.py`
- Health script: `scripts/stress/check_local_health.sh`
- Stress script: `scripts/stress/local_simulator_stress.sh`

Preflight:

- `curl http://localhost:8000/health`: passed
- `.venv/bin/pytest tools/simulator -q`: passed, `11 passed`
- `.venv/bin/pytest platform/backend/tests/test_mobile_ble_wifi_networks.py -q`: passed, `21 passed`
- `.venv/bin/pytest platform/backend/tests -q`: passed, `265 passed`

## Stage Results

| Stage | Scope | Duration | Report Directory | Result | Key Metrics |
| --- | --- | ---: | --- | --- | --- |
| 1 | 1 master, 1 camera, normal | 15m | `stress-reports/phase1-stage1-20260528-224608` | Pass | 102 recent events, max type 46 |
| 2 | `unstable_wifi` | 10m | `stress-reports/phase1-stage2-unstable_wifi-20260528-230124` | Pass | 106 recent events, max type 36 |
| 2 | `camera_disconnect` | 10m | `stress-reports/phase1-stage2-camera_disconnect-20260528-231125` | Pass | 102 recent events, max type 46 |
| 2 | `command_failure` | 10m | `stress-reports/phase1-stage2-command_failure-20260528-232127` | Pass | 105 recent events, max type 47 |
| 2 | `low_memory` | 10m | `stress-reports/phase1-stage2-low_memory-20260528-233128` | Pass | 106 recent events, max type 48 |
| 2 | `ota_failure` | 10m | `stress-reports/phase1-stage2-ota_failure-20260528-234129` | Pass | 104 recent events, max type 47 |
| 2 | `heartbeat_timeout` | 10m | `stress-reports/phase1-stage2-heartbeat_timeout-20260528-235130` | Pass | 101 recent events, max type 42 |
| 2 | `slow_command_ack` | 10m | `stress-reports/phase1-stage2-slow_command_ack-20260529-000132` | Pass | 105 recent events, max type 48 |
| 3 | 5 masters, 5 cameras, normal | 30m | `stress-reports/phase1-stage3-20260529-001147` | Pass | 101 recent events, max type 44 |
| 4 | 20 masters, 20 cameras, mixed `unstable_wifi`, `camera_disconnect`, `command_failure` | 30m | `stress-reports/phase1-stage4-mixed-20260529-004238` | Pass | 130 recent events, max type 33 |
| 5 | OTA success, isolated simulator device | 5m | `stress-reports/phase1-stage5-ota-success-isolated-api-20260529-013350` | Pass | 465 recent events, max type 194 |
| 5 | OTA failure, isolated simulator device | 5m | `stress-reports/phase1-stage5-ota-failure-isolated-api-20260529-013904` | Pass | 501 recent events, max type 209 |
| 6 | Image upload failure, isolated simulator device | 5m | `stress-reports/phase1-stage6-image-failure-isolated-20260529-014427` | Pass | 453 recent events, max type 205 |

## Focused Flow Evidence

OTA success, `device_id=11`:

- Commands: light, capture, and OTA all reached `completed`.
- Events included `COMMAND_QUEUED`, `COMMAND_SENT`, `COMMAND_ACKED`, `COMMAND_COMPLETED`, `OTA_STARTED`, `OTA_PREPARING`, `OTA_DOWNLOADING`, `OTA_VALIDATING`, `OTA_INSTALLING`, `OTA_REBOOTING`, and `OTA_SUCCESS`.

OTA failure, `device_id=12`:

- OTA command reached `failed`.
- Failure message: `Firmware checksum validation failed.`
- Events included `COMMAND_FAILED` and `OTA_FAILED`.

Image success, `device_id=11`:

- 39 image rows were created.
- Events included `IMAGE_UPLOAD_STARTED`, `IMAGE_CAPTURED`, and `IMAGE_UPLOADED`.

Image failure, `device_id=13`:

- Camera capture command reached `failed`.
- 0 image rows were created.
- Events included 38 `IMAGE_UPLOAD_FAILED` rows.

## Fixes Applied During Validation

- Added root-level `pytest.ini` so simulator tests can import the `tools` package when pytest chooses `tools/simulator` as root.
- Updated stale mobile onboarding source assertions in backend tests.
- Added isolated simulator device creation to `scripts/stress/local_simulator_stress.sh`.
- Changed stress OTA command creation to use the existing command API instead of direct DB insertion.
- Increased per-device diagnostic event retention from 100 to 1000 so command/OTA/image context survives noisy stress windows.
- Added a backend regression test to ensure command events survive a diagnostics burst.

## Recommendation

Local simulator stress validation passed after the retention and tooling fixes.

It is safe to proceed to Phase 2 local ESP32 OTA and image upload validation, with one caveat: use isolated simulator devices for simulator-only validation whenever a real ESP32 is connected to the same local backend.

## Remaining Risks

- Stage 1 through Stage 4 initially ran while a real ESP32 was also connected to the local backend. The backend still passed, but focused command/OTA validation was rerun on isolated simulator devices to remove this contamination.
- The 20-device run showed high simulator CPU usage on the laptop. Backend health remained stable, but larger local stress runs may be laptop-bound before backend-bound.
- The event retention cap is now higher. This preserves timeline context but increases local DB event volume during noisy periods.
