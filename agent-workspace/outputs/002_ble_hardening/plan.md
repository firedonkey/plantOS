# 1. Current Flow Summary

The ESP32 master firmware already has BLE onboarding in `device/esp32/src/provisioning/ble_provisioning.*`, BLE payload parsing in `device/esp32/src/provisioning/provisioning_payload.*`, and integration in `device/esp32/src/main.cpp`.

Current boot behavior:
- `setup()` calls `loadConfig()`.
- If `hasWifiCredentials()` is true, firmware attempts `connectToWiFi()`.
- If no Wi-Fi credentials are saved, firmware starts BLE provisioning with `startBleProvisioningMode()`.
- GPIO14 long press enters BLE provisioning when not already in provisioning mode.
- BLE advertises as `PlantLab-Setup-<chipSuffix>`.
- BLE exposes:
  - service `c7d36f9a-7b18-4c52-9c4f-93c2f0f6a901`
  - write characteristic `c7d36f9a-7b18-4c52-9c4f-93c2f0f6a902`
  - status characteristic `c7d36f9a-7b18-4c52-9c4f-93c2f0f6a903`
- BLE write callback parses JSON and sets one pending result.
- The main loop consumes the pending result in `serviceBleProvisioning()`.
- On valid payload, firmware writes Wi-Fi SSID/password, claim token, backend URL, and platform URL to `Preferences`, clears runtime `device_token` and `platform_device_id`, sets BLE status success, and schedules reboot.
- After reboot, firmware connects to Wi-Fi and calls `/api/devices/register-provisioned`.
- Backend registration returns `platform_device_id` and `device_access_token`; firmware stores them, clears `claim_token`, and resumes heartbeat/readings/commands through `PlatformClient`.

Current fallback behavior:
- Existing SoftAP provisioning remains in `startProvisioningMode()`.
- SoftAP is only entered automatically if BLE setup fails to start.
- SoftAP form submission saves directly through the same `saveConfig()` path and schedules reboot.
- Wi-Fi connection failure sets `DeviceMode::kWifiFailed` and `ProvisioningState::PROVISIONING_FAILED`; it does not automatically start BLE or SoftAP.
- BLE timeout after 10 minutes resumes saved Wi-Fi if prior credentials existed; otherwise it stops in failed state.

Current button and LED behavior:
- GPIO14 is handled by `PowerButton`.
- Main firmware only uses long press for BLE provisioning.
- Short press is reported by the button class but unused in main firmware.
- `clearConfig()` exists but is not wired to a user action.
- GPIO2 status LED supports only `kBooting`, `kOff`, `kNormal`, `kProvisioning`, and `kSleepPending`.
- `updateStatusLed()` maps BLE provisioning to provisioning blink, Wi-Fi connecting to boot blink, normal connected to solid on, and failure to off.

# 2. Problems / Risks Found

BLE state/race risks:
- `BleProvisioningService::handleWrite()` runs in a BLE callback and mutates `pending_result_` / `pending_result_ready_` without an explicit critical section or queue. A second write can overwrite the first pending result before `loop()` consumes it.
- Duplicate valid writes before reboot can repeatedly apply and save credentials.
- After success is reported, the write characteristic remains active until scheduled reboot, so a late write can race with the success/reboot window.
- BLE disconnect simply restarts advertising; this is good for recovery, but there is no explicit disconnected/connected state in status beyond `connected_`, and status does not tell the client whether a write is being committed.
- Timeout handling stops BLE but does not reset transient pending state or explicitly restore Wi-Fi mode before reconnect. It relies on later `connectToWiFi()` calls.
- BLE init failure automatically starts SoftAP. That preserves existing behavior but makes fallback behavior less deterministic because the device silently changes provisioning transport.

Credential/token risks:
- Wi-Fi password is not logged in the BLE accept log, which is good.
- Claim token is masked in the BLE accept log, and load logs only show `<set>`, which is good.
- `registerProvisionedDevice()` sends `claim_token` to the backend and does not log the request body, but the platform backend proxy logs failed registration payloads in `platform/backend/app/api/routes/devices.py`; that could log claim tokens server-side. This task is ESP32-focused, so do not change backend unless explicitly approved, but document the risk.
- `saveConfig()` only checks `ssid_written`. It ignores write results for password, claim token, device token, backend URL, platform URL, and platform id. A partial NVS write could be reported as success.
- BLE provisioning saves credentials before verifying that Wi-Fi connects or backend registration succeeds. If a user intentionally enters provisioning mode and provides bad data, old working credentials are overwritten.
- `applyBleProvisioningPayload()` clears old `device_token` and `platform_device_id` before `saveConfig()` proves all new fields were persisted.
- `clearConfig()` clears all preferences but is not exposed by button behavior, so credential clearing is currently a code path without a deterministic user flow.

Fallback risks:
- There are three effective provisioning/fallback paths: BLE, SoftAP, and compile-time/default secrets in `platform_secrets.h`.
- SoftAP is only used if BLE init fails, but its state is mislabeled as `PROVISIONING_BLE` in `g_provisioning_state`.
- Automatic SoftAP fallback after BLE init failure may surprise users and increase the active attack surface.
- Wi-Fi failure after saved credentials does not enter a clear recovery mode. The device remains in failed LED state and retries every `kReconnectRetryMs`.
- README mentions older power/touch behaviors that are not active in main firmware. Coder should not expand scope into touch behavior unless required.

Wi-Fi/BLE interaction risks:
- `startBleProvisioningMode()` disables Wi-Fi with `WiFi.mode(WIFI_OFF)`, which avoids radio contention during BLE provisioning.
- `connectToWiFi()` is blocking for up to `PLANTLAB_WIFI_CONNECT_TIMEOUT_MS`, which can delay button handling and status updates during Wi-Fi retries.
- When BLE times out with previous credentials, reconnect behavior relies on the normal loop, not a single explicit state transition helper.
- ESP-NOW setup is gated by `!g_provisioning_mode`, `g_wifi_ready`, and runtime registration, which is good and should not be broken.

# 3. Proposed BLE Onboarding State Machine

Keep the implementation small by extending the existing `ProvisioningState` enum and adding helper functions in `provisioning_payload.*` or a new small `provisioning_state.*` module that can be host-tested.

Recommended public states:
- `NORMAL`: runtime operation; Wi-Fi/backend path may run.
- `PROVISIONING_BLE`: BLE advertising and accepting one provisioning payload.
- `PROVISIONING_COMMITTING`: valid BLE payload received; writes are disabled while config is validated and persisted.
- `WIFI_CONNECTING`: Wi-Fi station connection in progress or retrying.
- `BACKEND_REGISTERING`: pending claim token is being exchanged for device token.
- `PROVISIONING_SUCCESS`: credentials accepted and saved; reboot or transition pending.
- `PROVISIONING_FAILED`: unrecoverable for the current attempt; old credentials should still be recoverable if present.
- `FALLBACK_SOFTAP`: SoftAP provisioning active.
- `FACTORY_RESET_PENDING`: button-triggered credential clear in progress.

Coder may keep enum names compact if flash/host-test constraints matter, but status JSON should expose stable string names.

State transitions:
- Boot with no saved Wi-Fi:
  - `NORMAL` or boot state -> `PROVISIONING_BLE`.
- Boot with saved Wi-Fi:
  - boot state -> `WIFI_CONNECTING`.
- Wi-Fi connected and no claim token:
  - `WIFI_CONNECTING` -> `NORMAL`.
- Wi-Fi connected and claim token exists:
  - `WIFI_CONNECTING` -> `BACKEND_REGISTERING`.
- Backend registration succeeds:
  - `BACKEND_REGISTERING` -> `NORMAL`.
- Backend registration fails:
  - remain in `BACKEND_REGISTERING`/retry state with normal Wi-Fi connected LED plus serial error, not automatic credential deletion.
- GPIO14 long press when not provisioning:
  - enter `PROVISIONING_BLE`.
  - preserve old config in memory/NVS until a full new commit succeeds.
- Valid BLE payload:
  - `PROVISIONING_BLE` -> `PROVISIONING_COMMITTING`.
  - stop accepting more writes immediately.
  - validate full payload and prepare a complete candidate config.
  - persist candidate atomically as far as `Preferences` allows.
  - on save success: `PROVISIONING_SUCCESS`, notify status, schedule reboot.
  - on save failure: keep previous runtime config if one existed, set `PROVISIONING_FAILED`, notify error, do not clear old NVS.
- Invalid BLE payload:
  - stay `PROVISIONING_BLE`.
  - update status characteristic with error.
  - do not save anything.
- BLE disconnect before valid payload:
  - stay `PROVISIONING_BLE`.
  - restart advertising.
  - do not reset timeout.
- BLE timeout:
  - if previous credentials existed: stop BLE, restore Wi-Fi station mode, transition to `WIFI_CONNECTING`.
  - if no previous credentials existed: transition to `PROVISIONING_FAILED`, keep retry available via reboot or long press.
  - do not automatically start SoftAP unless an explicit fallback policy below is approved.
- BLE init failure:
  - transition to `PROVISIONING_FAILED` by default.
  - optional explicit fallback: enter `FALLBACK_SOFTAP` only if compiled/configured or user requests fallback with a second long press.
- Factory reset:
  - enter `FACTORY_RESET_PENDING`.
  - stop BLE/SoftAP/Wi-Fi.
  - clear NVS.
  - reboot into BLE provisioning.

Idempotency rules:
- While in `PROVISIONING_COMMITTING` or `PROVISIONING_SUCCESS`, ignore further BLE writes and report `busy` or `already_committed`.
- Repeated invalid writes should not change saved config.
- Repeated identical valid writes before commit should be treated as one commit.
- Repeated long press while already provisioning should only refresh/log current state; it must not clear credentials.
- Reboot during provisioning before commit should preserve old config.
- Reboot after commit should boot into the newly saved candidate config.

# 4. Credential + Token Storage Rules

Sensitive logging:
- Never log Wi-Fi password.
- Never log raw BLE JSON.
- Never log full `plantlab_token`, `claim_token`, `device_token`, or `device_access_token`.
- Continue logging SSID only, because SSID is not a credential but can still be considered user-identifying; keep it only where useful.
- Use `maskSecretForLog()` for any token-like value in firmware logs.
- Add a separate helper such as `maskUrlForLog()` only if URL query strings can contain tokens; otherwise log platform/backend base URLs as currently done.
- Do not echo secrets in BLE status JSON.

Payload acceptance:
- Required BLE fields remain:
  - `ssid`
  - `password`
  - `plantlab_token`
  - `platform_url`, unless a fallback platform URL exists
- Continue accepting aliases:
  - `wifi_ssid`
  - `wifi_password`
  - `setup_code`
  - `claim_token`
- Continue rejecting direct `device_access_token` or `device_token` payloads. Existing backend flow needs `platform_device_id` plus the long-term token, so direct token provisioning is out of scope.
- Keep max lengths:
  - JSON: `kProvisioningMaxJsonLength`
  - SSID: 32
  - password: 63
  - token: 256
  - URL: 256
- Add host tests for blank string trimming and aliases if not already exhaustive.

Save/commit behavior:
- Do not mutate `g_config` in place until the payload has passed parser validation.
- Build a local `DeviceConfig candidate`.
- Preserve an `old_config` snapshot before saving.
- Candidate from BLE should set:
  - `wifi_ssid = payload.ssid`
  - `wifi_password = payload.password`
  - `claim_token = payload.plantlab_token`
  - `backend_url = payload.backend_url`
  - `platform_url = payload.platform_url`
  - `device_token = ""`
  - `platform_device_id = 0`
- Save candidate through a new helper such as `saveConfigCandidate(const DeviceConfig&)`.
- Check every `Preferences` write result where available:
  - non-empty strings should report bytes written greater than zero
  - empty strings are acceptable only for fields intentionally cleared
  - `putInt()` should be checked for expected byte count if the API returns it
- If any write fails:
  - restore `g_config = old_config`
  - call `rebuildPlatformClient()`
  - report save failure
  - do not schedule reboot
- If all writes succeed:
  - assign `g_config = candidate`
  - rebuild platform client, which will be disabled until backend registration completes
  - notify BLE success
  - schedule reboot

Atomicity:
- ESP32 `Preferences` does not provide a true multi-key transaction.
- Keep the implementation small by using a staged config marker:
  - before writing candidate keys, write `provisioning_commit = "pending"` or `config_generation_pending`.
  - write all candidate keys.
  - write `provisioning_commit = "complete"` or update a monotonically increasing generation marker last.
  - on boot, if marker is `pending`, treat config as incomplete and recover to prior config if a backup exists, or enter failed BLE provisioning if no valid config exists.
- If backup/generation support is too large, minimum acceptable implementation is to verify every write and avoid mutating runtime config until all writes succeed.
- Do not introduce encrypted NVS in this task; document that flash/NVS encryption is a separate board/security configuration task.

Credential clearing:
- Only clear credentials on explicit user action, not on Wi-Fi failure or backend registration failure.
- Factory reset should clear:
  - Wi-Fi SSID/password
  - claim token
  - device token
  - platform id
  - backend/platform URLs
  - camera provisioning runtime state
- Factory reset should not be triggered by a normal provisioning timeout.
- After clear, reboot and start BLE provisioning.

# 5. Fallback Cleanup Plan

Fallback paths to keep:
- Saved Wi-Fi retry loop: keep it. It is necessary for normal network outages.
- BLE provisioning: primary onboarding path.
- SoftAP code: keep compiled for now because it is existing working behavior and useful if BLE cannot start.
- Compile-time `platform_secrets.h` fallbacks: keep for developer smoke tests and direct lab bring-up.

Fallback paths to gate/simplify:
- Do not automatically enter SoftAP just because BLE times out.
- Change BLE init failure behavior from unconditional SoftAP fallback to deterministic policy:
  - preferred: set `PROVISIONING_FAILED` and log `ble_init_failed`; user can long-press again or use an explicit fallback action.
  - acceptable if approved: start SoftAP only after BLE init failure when no previous Wi-Fi credentials exist.
- Rename or distinguish SoftAP state from BLE state:
  - use `FALLBACK_SOFTAP` or map `g_softap_provisioning_active` to distinct status/LED behavior.
- If SoftAP remains automatic on BLE init failure, log one explicit line:
  - `[provisioning] fallback=softap reason=ble_init_failed`
- Do not start SoftAP automatically after Wi-Fi connection failure with saved credentials. That can create confusing loops and expose setup mode during ordinary router outages.
- Do not clear old credentials on Wi-Fi failure. Keep retrying and allow explicit long press for reprovisioning.

Fallback paths to avoid/remove from active flow:
- No automatic loop: BLE -> timeout -> SoftAP -> save -> reboot -> Wi-Fi fail -> BLE.
- No implicit credential overwrite from compile-time secrets when NVS has valid credentials.
- Do not wire legacy touch-button factory reset into main firmware unless explicitly approved. GPIO14 is already the provisioning button through `PowerButton`.

Deterministic fallback matrix:
- No credentials, BLE starts: BLE active.
- No credentials, BLE init fails: failed LED; optional explicitly approved SoftAP fallback.
- Existing credentials, BLE starts by long press: BLE active; timeout resumes saved Wi-Fi.
- Existing credentials, invalid BLE payload: remain BLE; old credentials untouched.
- Existing credentials, valid BLE payload: overwrite only after explicit long-press entry and successful commit.
- Existing credentials, Wi-Fi outage: retry saved Wi-Fi; no SoftAP/BLE auto-entry.
- Factory reset: clear all config; reboot into BLE.

# 6. Button + LED Behavior

GPIO assignments:
- Provisioning button: GPIO14 via `PIN_POWER_BUTTON`.
- Status LED: GPIO2 via `PIN_STATUS_LED`.

Button behavior for this task:
- Short press:
  - no production behavior change by default.
  - optional: brief LED feedback only if already implemented cleanly.
  - do not implement deep sleep in this task despite README mentioning older behavior.
- Long press, 5 seconds:
  - if not provisioning: enter BLE provisioning.
  - if already BLE provisioning: restart advertising or refresh status only; do not clear credentials.
  - if SoftAP fallback active: leave SoftAP active; do not switch transports unless explicitly designed.
- Very long press, recommended 10 seconds:
  - factory reset / credential clear.
  - Coder can implement by extending `PowerButton` or adding a separate held-duration check in `checkProvisioningButton()`.
  - require continuous hold and log countdown/state.
  - set LED factory reset pattern before clearing.
- Do not use capacitive `TouchButtonManager` in main firmware for this task unless explicitly approved; it shares GPIO14 and would expand scope.

LED states:
- Normal boot:
  - slow blink, existing `StatusLedMode::kBooting`.
- BLE provisioning active:
  - fast blink, existing `StatusLedMode::kProvisioning`.
- Wi-Fi connecting:
  - slow blink, existing `kBooting`, or add a distinct medium blink if changing `StatusLed`.
- Backend registration/heartbeat success:
  - solid on, existing `kNormal`.
  - heartbeat upload should not flicker the LED on every send.
- Provisioning failed:
  - distinct failure pattern, not just off.
  - recommended: add `StatusLedMode::kError` as two quick pulses every 2 seconds.
- Fallback SoftAP mode:
  - distinct from BLE, recommended `StatusLedMode::kFallback` with triple blink or slower provisioning blink.
- Factory reset / credential clear:
  - rapid blink for 2 seconds, then reboot.
  - can reuse `signal_user_feedback()` only if visible enough; otherwise add `kFactoryReset`.
- Reboot scheduled after successful provisioning:
  - success pattern, recommended solid on or quick success pulses until restart.

Likely `StatusLedMode` additions:
- `kError`
- `kFallback`
- `kFactoryReset`
- optional `kCommitting`

Keep LED implementation simple and deterministic; do not add complex animation state beyond mode-based blink patterns.

# 7. Wi-Fi/BLE Coordination Rules

Radio ownership:
- BLE provisioning owns the radio while active.
- On entering BLE provisioning:
  - set `g_provisioning_mode = true`
  - set `g_wifi_ready = false`
  - disconnect Wi-Fi
  - set `WiFi.mode(WIFI_OFF)`
  - pause ESP-NOW/camera provisioning through existing `g_provisioning_mode` gates
- During BLE provisioning:
  - do not call `connectToWiFi()`
  - do not call `setupEspNow()`
  - do not service camera provisioning/capture scheduling
  - keep pump update and LED update running
- On invalid BLE payload:
  - keep BLE active
  - do not touch Wi-Fi or saved config
- On BLE timeout with previous config:
  - stop BLE cleanly
  - set `g_provisioning_mode = false`
  - set `g_device_mode = kConnecting`
  - set `g_provisioning_state = WIFI_CONNECTING`
  - reset `g_last_wifi_attempt_ms = 0`
  - let `connectToWiFi()` take over
- On BLE success:
  - stop accepting writes
  - notify success
  - schedule reboot
  - do not attempt Wi-Fi connection before reboot unless Coder intentionally changes the flow and tests it on hardware
- On SoftAP:
  - SoftAP owns Wi-Fi AP mode.
  - Do not run BLE and SoftAP simultaneously.
  - Stop BLE before SoftAP starts.
- On normal Wi-Fi reconnect:
  - do not start BLE automatically just because connection failed.
  - retry with backoff as currently done.

Blocking behavior:
- Avoid adding more blocking delays to BLE or Wi-Fi paths.
- Existing `connectToWiFi()` blocks for up to `PLANTLAB_WIFI_CONNECT_TIMEOUT_MS`; do not increase this.
- If Coder touches Wi-Fi connection logic, prefer a staged/non-blocking retry only if it stays small. Otherwise preserve current behavior.

# 8. Backend Impact

No backend changes are required for the ESP32 BLE hardening implementation.

Existing flow to preserve:
- BLE payload carries the PlantLab setup/claim token, not the long-term device token.
- Firmware calls platform backend `POST /api/devices/register-provisioned`.
- Platform backend proxies to provisioning backend `/api/devices/register`.
- Response includes `platform_device_id` and `device_access_token`.
- Firmware stores `platform_device_id` and `device_token`.
- Runtime `PlatformClient` sends `X-Device-Token` for:
  - `/api/hardware/heartbeat`
  - `/api/hardware/readings`
  - `/api/hardware/commands/pending`
  - command result endpoints
  - image upload path where applicable

Backend caution:
- `platform/backend/app/api/routes/devices.py` logs failed registration payloads and may include `claim_token`. This is a backend security cleanup candidate, but it is outside this ESP32-only task unless approval expands scope.
- Do not change backend API contracts, schema, token generation, or heartbeat behavior in this task.

# 9. Files Likely To Change

High-risk files:
- `device/esp32/src/main.cpp`
  - Central boot/provisioning/Wi-Fi/backend loop.
  - Risk: breaking normal Wi-Fi, heartbeat, camera ESP-NOW, or existing SoftAP.
- `device/esp32/src/provisioning/ble_provisioning.cpp`
  - BLE callbacks and pending result handoff.
  - Risk: callback races, advertising restart issues, status notifications.
- `device/esp32/src/provisioning/provisioning_payload.cpp`
  - Parser and state helper behavior.
  - Risk: breaking mobile/web payload compatibility.
- `device/esp32/src/system/status_led.cpp`
  - LED mode patterns.
  - Risk: confusing hardware feedback if modes overlap.
- `device/esp32/src/system/power_button.cpp`
  - Only if very-long-press support is added to the shared button class.
  - Risk: changing button behavior in dedicated tests.

Expected production files:
- `device/esp32/src/main.cpp`
- `device/esp32/src/provisioning/ble_provisioning.h`
- `device/esp32/src/provisioning/ble_provisioning.cpp`
- `device/esp32/src/provisioning/provisioning_payload.h`
- `device/esp32/src/provisioning/provisioning_payload.cpp`
- `device/esp32/src/system/status_led.h`
- `device/esp32/src/system/status_led.cpp`
- Optional: `device/esp32/src/system/power_button.h`
- Optional: `device/esp32/src/system/power_button.cpp`

Expected tests:
- `device/esp32/tests_host/test_ble_provisioning_payload.cpp`
- Optional new host test:
  - `device/esp32/tests_host/test_provisioning_state.cpp`
  - or fold state tests into existing BLE payload host test
- Optional firmware smoke target updates only if needed:
  - `device/esp32/src/tests/button_status_led_test_main.cpp`

Expected docs only if Coder is allowed to update docs:
- `device/esp32/README.md`

Do not change unless explicitly approved:
- `platform/backend/**`
- `provision_backend/**`
- mobile/web onboarding UI
- camera node runtime/provisioning code
- unrelated sensor/actuator modules

# 10. Implementation Steps For Coder

1. Add/extend state definitions.
   - Extend `ProvisioningState` with committing, registering, fallback, and factory reset states if the names fit current code style.
   - Add `provisioningStateName()` mappings and host tests.
   - Add parse/status error codes:
     - `busy`
     - `save_failed`
     - `timeout`
     - `ble_init_failed`
     - optional `already_committed`

2. Harden BLE pending-result handoff.
   - Prevent callback overwrite by adding a small pending slot guard:
     - if a result is pending, reject/ignore subsequent writes and set status `busy`.
   - Add a `committed_` or `accepting_writes_` flag to `BleProvisioningService`.
   - Once valid payload is accepted by main loop, disable writes logically even if the characteristic still exists until reboot.
   - Keep callbacks lightweight; main loop remains responsible for persistence and reboot.

3. Add explicit BLE status behavior.
   - Status JSON should include:
     - `state`
     - `ready`
     - optional `error`
     - optional `rebooting`
   - Do not include SSID, password, token, platform URL with query strings, or raw payload.
   - Ensure invalid payload leaves `ready=true`.
   - Ensure committing/success leaves `ready=false`.

4. Refactor config persistence safely.
   - Add `DeviceConfig makeConfigFromBlePayload(const BleProvisioningPayload&)` or equivalent helper.
   - Add `saveConfigCandidate(const DeviceConfig&)`.
   - Check every `Preferences` write result.
   - Do not mutate global `g_config` until save succeeds.
   - On save failure, keep old runtime config and platform client.
   - Minimum acceptable recovery: no partial runtime mutation. Preferred recovery: add a small pending/complete marker.

5. Update BLE apply flow in `serviceBleProvisioning()`.
   - For invalid payload: log error code only, no save.
   - For valid payload:
     - log SSID and masked token only.
     - transition to committing.
     - disable further BLE writes.
     - save candidate.
     - on success: set success status, schedule reboot.
     - on failure: set failed status with `save_failed`, resume old config if available.

6. Clean fallback logic.
   - Replace automatic SoftAP fallback on BLE init failure with deterministic policy.
   - Recommended default:
     - if prior credentials exist: stop BLE attempt and resume Wi-Fi.
     - if no credentials exist: set failed state and keep LED error.
   - If SoftAP fallback is retained automatically, gate it with a named boolean/constant and log the reason.
   - Add distinct `FALLBACK_SOFTAP` state when SoftAP is active.

7. Add factory reset behavior.
   - Implement explicit GPIO14 very-long-press credential clear.
   - Keep 5-second long press for BLE provisioning.
   - Recommended 10-second hold for factory reset.
   - On factory reset:
     - set LED factory reset mode
     - stop BLE/SoftAP
     - disconnect Wi-Fi
     - call `clearConfig()`
     - schedule reboot
   - Avoid accidental reset by firing only once per continuous hold.

8. Update LED modes.
   - Add `kError`, `kFallback`, and `kFactoryReset` to `StatusLedMode`.
   - Update `StatusLed::update()` patterns.
   - Update `updateStatusLed()` mapping.
   - Keep existing modes and behavior for normal boot/connected.

9. Preserve backend/runtime behavior.
   - Do not change `registerProvisionedDevice()` API contract except optional state logging/status assignment.
   - Do not change `PlatformClient` auth header behavior.
   - Ensure camera provisioning remains gated while provisioning is active.

10. Add host tests.
   - Extend `test_ble_provisioning_payload.cpp` for new states/errors.
   - Add tests for duplicate/busy state helpers if implemented outside BLE hardware callbacks.
   - Add tests for direct device token rejection remains intact.
   - Add tests for timeout transition with and without previous config.
   - Add tests for secret masking and no raw token helper output.

11. Build and smoke-check.
   - Run host tests first.
   - Build main firmware environments.
   - If hardware is available, run manual validation checklist below.

# 11. Test Plan

Host/parser tests:
- Successful BLE onboarding payload with `ssid`, `password`, `plantlab_token`, `platform_url`.
- Successful alias payload with `wifi_ssid`, `wifi_password`, `setup_code`.
- Successful alias payload with `claim_token`.
- Missing SSID returns `missing_ssid`.
- Blank SSID returns `missing_ssid`.
- Missing password returns `missing_password`.
- Blank password returns `missing_password`.
- Missing device/setup token returns `missing_token`.
- Blank token returns `missing_token`.
- Missing platform URL with no fallback returns `missing_platform_url`.
- Missing platform URL with fallback succeeds.
- Invalid JSON returns `invalid_json`.
- Non-object JSON returns `malformed_payload`.
- Oversized JSON returns `payload_too_large`.
- Overlong SSID/password/token/URL return specific length errors.
- Direct `device_token` and `device_access_token` remain rejected.
- `maskSecretForLog()` masks short and long tokens.
- Any new state/error name returns stable expected string.

State/logic tests:
- Invalid payload keeps state in BLE provisioning and does not request save.
- Valid payload transitions to committing/success and disables additional writes.
- Duplicate write while pending returns/sets `busy`.
- Timeout with previous credentials returns `WIFI_CONNECTING`.
- Timeout without previous credentials returns `PROVISIONING_FAILED`.
- Save failure returns `PROVISIONING_FAILED` and preserves old config in helper-level logic.
- Factory reset transition requires explicit reset event, not timeout or invalid payload.

Firmware build checks:
- `cd device/esp32 && pio run -e esp32-s3-devkitc-1`
- `cd device/esp32 && pio run -e esp32-local`
- `cd device/esp32 && pio run -e esp32-gcp`
- If button/LED shared classes change, build `button_status_led_test` environment if available in `platformio.ini`.
- If host tests are run through pytest:
  - `pytest platform/backend/tests/test_esp32_ble_provisioning_host.py`
- If compiling host test manually, use the existing clang command pattern from `test_esp32_ble_provisioning_host.py`.

Manual test cases:
- Successful BLE onboarding:
  - clear credentials
  - boot
  - connect BLE client
  - write valid payload
  - confirm success status/reboot/Wi-Fi/backend heartbeat
- Invalid payload:
  - write malformed JSON
  - verify error status
  - verify no reboot and no config overwrite
- Missing SSID:
  - verify `missing_ssid`
- Missing password:
  - verify `missing_password`
- Missing device/setup token:
  - verify `missing_token`
- Disconnect during onboarding:
  - connect BLE client, disconnect before write
  - verify advertising resumes until timeout
- Timeout during onboarding:
  - leave BLE active past timeout
  - verify no-credential device enters failed state
  - verify existing-credential device resumes Wi-Fi
- Repeated provisioning attempts:
  - send invalid then valid payload
  - send duplicate valid payload before reboot
  - verify only one commit/reboot path
- Reboot during provisioning:
  - reboot before valid write
  - verify old config remains
- Existing valid credentials not overwritten accidentally:
  - boot with valid saved config
  - do not press button
  - verify BLE does not start and credentials remain
  - long press starts BLE but invalid/timeout does not overwrite
- Fallback behavior:
  - simulate BLE init failure if practical
  - verify deterministic failed state or approved SoftAP fallback
- No secret logging:
  - monitor serial during valid/invalid onboarding and backend registration
  - verify password and full token never appear
- Existing Wi-Fi/backend heartbeat:
  - with existing valid config, boot and verify normal heartbeat/readings/commands still work

# 12. Manual Hardware Validation Checklist

Hardware:
- Board is ESP32-S3-DevKitC-1-N32R16V.
- Status LED is wired to GPIO2.
- Provisioning button is wired to GPIO14 active-low with pull-up behavior.
- Serial monitor at 115200 baud.

BLE onboarding:
- Device with erased NVS starts BLE provisioning automatically.
- BLE advertised name is `PlantLab-Setup-<suffix>`.
- GPIO2 shows BLE provisioning pattern.
- BLE status characteristic initially reports provisioning ready.
- Valid payload returns success and rebooting status.
- Device reboots after success delay.
- Device connects to the submitted Wi-Fi.
- Device exchanges claim token for device token.
- Hardware heartbeat appears in backend.
- Full password/token do not appear in serial output.

Existing credentials:
- Device with saved valid credentials boots directly to Wi-Fi.
- BLE does not advertise during normal boot.
- Long press enters BLE provisioning.
- BLE timeout resumes old Wi-Fi.
- Invalid BLE payload does not alter old credentials.
- Valid BLE payload intentionally replaces old credentials only after successful save.

Button/reset:
- Short press does not unexpectedly clear credentials or enter sleep.
- 5-second long press enters BLE provisioning.
- 10-second hold, if implemented, clears credentials and reboots.
- Factory reset LED pattern is visible before reboot.
- After factory reset, device boots into BLE provisioning.

Fallback:
- BLE init failure behavior matches approved policy.
- SoftAP, if enabled as fallback, uses a distinct LED/state and logs clear reason.
- Wi-Fi outage does not start BLE or SoftAP automatically.
- Saved Wi-Fi retry continues after router comes back.

Regression:
- Pump/light initialization remains off/safe at boot.
- Sensor reads continue after normal connection.
- Camera ESP-NOW provisioning/capture still runs only after Wi-Fi and backend registration.
- Manual capture command path still reports command status.

# 13. Non-goals

- Do not redesign backend provisioning, token generation, schema, or auth.
- Do not implement mobile/web BLE UI in this task.
- Do not remove SoftAP code unless separately approved.
- Do not add encrypted NVS or flash encryption configuration.
- Do not implement direct long-term device token provisioning.
- Do not redesign ESP-NOW camera provisioning.
- Do not change sensor, actuator, command, or image upload behavior except where provisioning gating requires preservation.
- Do not introduce broad refactors of `main.cpp`; keep changes localized around provisioning helpers and state transitions.
- Do not wire capacitive touch behavior into production main firmware for this task.

# 14. Open Questions / Assumptions

Assumptions:
- BLE payload should continue to carry the temporary PlantLab setup/claim token, not the long-term device access token.
- Existing `/api/devices/register-provisioned` flow is the source of `platform_device_id` and `device_access_token`.
- It is acceptable to keep reboot-after-save behavior instead of connecting immediately after BLE commit.
- SoftAP remains available but should be gated and deterministic.
- GPIO14 long press is the intended explicit user action for reprovisioning.
- Very-long-press factory reset is acceptable if approved; otherwise Coder should leave credential clear unwired.
- Host-testable parser/state logic is preferred over BLE-hardware-only testing.

Open questions:
- Should BLE init failure automatically start SoftAP when no credentials exist, or should it stay failed until explicit user action?
- Should factory reset be implemented now as a GPIO14 10-second hold, or only designed for later?
- Should Coder add a staged NVS commit marker, or is full write-result checking enough for this hardening pass?
- Should the backend proxy token logging risk be handled in a separate backend security task?

Explicit approval checklist:
- [ ] Approve BLE as primary onboarding when no Wi-Fi credentials exist.
- [ ] Approve GPIO14 5-second long press entering BLE provisioning.
- [ ] Approve preserving old credentials unless a valid payload is intentionally committed.
- [ ] Approve rejecting direct long-term device token provisioning.
- [ ] Approve no backend changes for this task.
- [ ] Approve deterministic SoftAP fallback policy.
- [ ] Approve adding LED modes for error, fallback, and factory reset.
- [ ] Approve optional GPIO14 10-second factory reset behavior.
- [ ] Approve small persistence hardening around `Preferences`.
- [ ] Approve host tests for parser/state logic before hardware testing.