# 1. Summary

Add BLE provisioning as the primary ESP32 master-node onboarding path while keeping the existing SoftAP provisioning code available as a fallback. The BLE flow will reuse the current storage and backend registration path: receive Wi-Fi credentials plus the PlantLab setup/claim token over BLE, save them to NVS via `Preferences`, reboot, connect to Wi-Fi, call the existing `/api/devices/register-provisioned` path, store the returned long-term device token, then resume heartbeats/readings/commands.

Important interpretation: the current firmware/backend flow uses a temporary `claim_token`/`setup_code` during provisioning and receives the long-term `device_access_token` from the backend after registration. The BLE payload should carry that setup/claim token as the PlantLab provisioning token. Directly accepting a long-term device token is out of scope unless approved separately because the current runtime also needs `platform_device_id`.

# 2. Scope

In scope:
- ESP32-S3 master firmware only.
- Long-press GPIO14 enters BLE provisioning mode.
- GPIO2 LED indicates provisioning mode using the existing provisioning blink pattern.
- BLE GATT service accepts a JSON provisioning payload.
- Payload validation for missing/empty fields, malformed JSON, and length limits.
- Safe handling for invalid payloads, BLE disconnects, and provisioning timeout.
- Secret masking utilities for token/password-safe logs.
- NVS/`Preferences` storage using existing config keys.
- Existing device token registration behavior preserved.
- Existing SoftAP provisioning retained, not deleted.
- Unit-testable parsing/state logic.
- ESP32 documentation update for BLE usage.

Out of scope:
- Backend schema or API changes.
- Web/mobile BLE UI implementation.
- Removing SoftAP provisioning.
- Full at-rest NVS encryption rollout unless the repo already has flash/NVS encryption configuration available.
- Direct provisioning with a long-term device access token unless a `platform_device_id` payload contract is explicitly approved.

# 3. Proposed design

BLE architecture:
- Add a small BLE provisioning module under `device/esp32/src/provisioning/`.
- Use a custom GATT service advertised only while provisioning is active.
- Recommended advertised name: `PlantLab-Setup-<chipSuffix>`, where `<chipSuffix>` comes from `stableHardwareDeviceId()`.
- Use NimBLE-Arduino or the ESP32 Arduino BLE stack. Prefer NimBLE-Arduino for ESP32-S3 memory usage if PlatformIO resolves it cleanly.
- GATT shape:
  - Service UUID: fixed PlantLab provisioning UUID.
  - Write characteristic UUID: client writes provisioning JSON with response.
  - Status characteristic UUID: read/notify current status JSON.
- The BLE callback should only parse/copy the request and set a pending result flag. Main loop should perform config mutation, NVS writes, Wi-Fi/BLE stop, and restart scheduling.

Provisioning payload:
```json
{
  "ssid": "HomeWiFi",
  "password": "wifi-password",
  "plantlab_token": "setup-or-claim-token",
  "platform_url": "https://api-or-platform.example",
  "backend_url": "https://provisioning.example"
}
```
- Required: `ssid`, `password`, `plantlab_token`.
- `platform_url` is optional only if `PLANTLAB_PLATFORM_URL` or existing runtime platform URL is configured.
- `backend_url` is optional and should be saved for compatibility with the current config shape.
- Accept aliases for compatibility: `wifi_ssid`, `wifi_password`, `setup_code`, `claim_token`.
- Reject direct `device_access_token` mode unless payload also includes `platform_device_id`; do not implement this path without explicit approval.

Provisioning state machine:
- Add a testable state enum with these public names:
  - `NORMAL`
  - `PROVISIONING_BLE`
  - `WIFI_CONNECTING`
  - `PROVISIONING_FAILED`
  - `PROVISIONING_SUCCESS`
- Transitions:
  - Boot with complete runtime registration -> `NORMAL`.
  - Boot without Wi-Fi credentials -> `PROVISIONING_BLE`.
  - GPIO14 long press -> `PROVISIONING_BLE`.
  - Valid BLE payload saved -> `PROVISIONING_SUCCESS`, notify client, stop BLE, schedule reboot.
  - Reboot with Wi-Fi plus pending claim token -> `WIFI_CONNECTING`, then existing registration path.
  - Registration success -> existing `device_token` saved, `claim_token` cleared, `NORMAL`.
  - Invalid payload -> stay `PROVISIONING_BLE`, notify error, do not save.
  - BLE disconnect before valid write -> stay `PROVISIONING_BLE` until timeout.
  - Timeout -> `PROVISIONING_FAILED`; if previous valid config exists, stop BLE and resume normal connection, otherwise keep safe failed indication and optionally fall back to SoftAP.

Security design:
- Never log Wi-Fi password.
- Never log raw BLE JSON.
- Never log full `plantlab_token`, `claim_token`, or `device_token`.
- Add a shared helper such as `maskSecretForLog()` returning first/last 4 chars for longer tokens and all `*` for short tokens.
- Existing registration logs should remain token-safe.
- BLE status responses should use error codes, not echo submitted secrets.
- Save only after full payload validation succeeds.
- Keep credentials in NVS via existing `Preferences` keys. Document that this is non-volatile ESP32 storage; true encrypted NVS requires separate flash/NVS encryption configuration.

Storage design:
- Reuse existing namespace and keys:
  - `plantlab/wifi_ssid`
  - `plantlab/wifi_pass`
  - `plantlab/claim_token`
  - `plantlab/device_token`
  - `plantlab/platform_id`
  - `plantlab/backend_url`
  - `plantlab/platform_url`
- BLE provisioning writes `wifi_ssid`, `wifi_pass`, `claim_token`, optional URLs, clears `device_token` and `platform_id`.
- Existing `registerProvisionedDevice()` continues to exchange `claim_token` for `device_token`.
- Do not alter token header behavior in `PlatformClient`.

API/backend impact:
- No required backend change.
- BLE transport replaces the local SoftAP form transport, but it feeds the same firmware config and backend registration flow.
- `/api/devices/register-provisioned` and provisioning service `/api/devices/register` remain unchanged.
- Existing `X-Device-Token` heartbeat/readings/commands behavior remains unchanged.

# 4. Files likely to change

- `device/esp32/platformio.ini`
  - Add BLE library dependency to main ESP32 environments if needed.
  - Add a native/host test target if selected by Coder.
- `device/esp32/src/main.cpp`
  - Integrate BLE provisioning start/stop, state transitions, button behavior, timeout servicing, and save/reboot flow.
  - Keep SoftAP functions in place.
- `device/esp32/src/provisioning/ble_provisioning.h`
- `device/esp32/src/provisioning/ble_provisioning.cpp`
  - BLE GATT service wrapper and callbacks.
- `device/esp32/src/provisioning/provisioning_payload.h`
- `device/esp32/src/provisioning/provisioning_payload.cpp`
  - JSON parsing, field validation, error enum, and secret masking.
- `device/esp32/tests_host/test_ble_provisioning_payload.cpp`
  - Parser/masking/state tests.
- `device/esp32/README.md`
  - BLE provisioning instructions and example payload.
- Optional: `docs/design/ble_provisioning_design.md`
  - Only if the Coder needs a separate design doc; keep concise.

# 5. Implementation steps

1. Add the payload module.
   - Define `BleProvisioningPayload`, `ProvisioningParseResult`, and error codes.
   - Implement JSON parsing with ArduinoJson.
   - Enforce field length limits: SSID <= 32, password <= 63, token <= existing backend/schema practical max, URLs bounded.
   - Add alias handling for `setup_code`/`claim_token`.

2. Add secret masking.
   - Implement `maskSecretForLog()`.
   - Use it in new BLE/provisioning logs.
   - Do not print submitted password or full tokens.

3. Add state helper logic.
   - Add `ProvisioningState`.
   - Add small transition/service helpers that can be host-tested without BLE hardware.
   - Map `PROVISIONING_BLE` to existing `StatusLedMode::kProvisioning`.
   - Map `WIFI_CONNECTING` to existing booting blink and `PROVISIONING_FAILED` to a distinct safe indication if practical.

4. Add BLE service wrapper.
   - Start advertising only inside BLE provisioning mode.
   - Write characteristic parses payload and reports status.
   - Status characteristic returns JSON such as:
     - `{"state":"PROVISIONING_BLE","ready":true}`
     - `{"state":"PROVISIONING_FAILED","error":"missing_ssid"}`
     - `{"state":"PROVISIONING_SUCCESS","rebooting":true}`
   - On disconnect, continue advertising until timeout.

5. Integrate with `main.cpp`.
   - Add `startBleProvisioningMode()` and `stopBleProvisioningMode()`.
   - On boot without saved Wi-Fi credentials, start BLE provisioning by default.
   - On GPIO14 long press, enter BLE provisioning without deleting existing working credentials until a valid new payload is saved.
   - Preserve SoftAP function and route code. If BLE init fails, optionally call existing `startProvisioningMode()` as fallback.
   - On valid BLE payload, copy into `g_config`, clear old runtime registration fields, call existing `saveConfig()`, notify success, and schedule reboot.
   - After reboot, leave existing `connectToWiFi()` and `registerProvisionedDevice()` behavior intact.

6. Add timeout handling.
   - Define a timeout, e.g. 10 minutes.
   - Service it in `loop()`.
   - On timeout with prior complete runtime config, stop BLE and reconnect normally.
   - On timeout without prior config, enter `PROVISIONING_FAILED` and allow another long press or reboot to retry.

7. Update docs.
   - Explain GPIO14 long press.
   - List BLE service/characteristic UUIDs.
   - Provide example JSON.
   - Provide example with a generic BLE client such as nRF Connect/LightBlue or a simple Web Bluetooth script.
   - Note SoftAP still exists as fallback.

# 6. Test and verification plan

Unit/host tests:
- Valid payload with `ssid`, `password`, `plantlab_token`.
- Valid payload using aliases `wifi_ssid`, `wifi_password`, `setup_code`.
- Missing SSID.
- Missing password.
- Missing token.
- Invalid JSON.
- Malformed or non-object JSON.
- Overlong SSID/password/token/URL.
- Secret masking for short and long tokens.
- State transitions for success, invalid payload, disconnect, timeout, and previous-config recovery.

Firmware build checks:
- `cd device/esp32 && pio run -e esp32-s3-devkitc-1`
- `cd device/esp32 && pio run -e esp32-local`
- `cd device/esp32 && pio run -e esp32-gcp`
- Run any added native/host test command.

Manual BLE verification:
- Flash ESP32-S3 master.
- Long-press GPIO14 for existing configured device.
- Confirm GPIO2 provisioning blink.
- Connect to `PlantLab-Setup-<chipSuffix>`.
- Write valid JSON to the provisioning write characteristic.
- Confirm success status notification and reboot.
- Confirm Wi-Fi connects.
- Confirm backend registration exchanges claim token for device token.
- Confirm `/api/hardware/heartbeat` resumes with `X-Device-Token`.
- Repeat invalid payload cases and verify no save/reboot.
- Disconnect mid-provisioning and verify advertising continues until timeout.
- Verify serial logs never contain password or full token.

Regression verification:
- Existing SoftAP provisioning still compiles and remains reachable through fallback path.
- Existing Wi-Fi reconnect flow still works.
- Existing backend heartbeat, readings, command polling, and camera ESP-NOW provisioning still work.
- Existing device-token behavior in `PlatformClient` unchanged.

# 7. Risks and open questions

- Token terminology is ambiguous. Current firmware uses `claim_token` during provisioning and stores backend-returned `device_token` afterward. Approval should confirm BLE sends the setup/claim token, not a long-term device access token.
- If direct long-term device token provisioning is required, the payload must also include `platform_device_id`; this is a separate design path.
- ESP32 Arduino `Preferences` stores in NVS but may not be encrypted unless flash/NVS encryption is configured. This plan keeps storage compatible and documents the limitation.
- BLE library choice can affect flash/RAM usage. NimBLE is preferred, but Coder should confirm PlatformIO compatibility before committing.
- BLE write payload size depends on MTU/client behavior. Keep payload compact and document one-shot JSON write limits.
- Running BLE and Wi-Fi simultaneously can increase memory pressure. This design stops BLE after successful provisioning before reboot/connect.
- SoftAP fallback trigger needs approval if BLE init fails: automatic fallback is useful, but it briefly preserves the old onboarding surface.

# 8. Explicit approval checklist

- [ ] Approve BLE as the default provisioning mode on boot when no Wi-Fi credentials exist.
- [ ] Approve GPIO14 long press entering BLE provisioning.
- [ ] Approve preserving SoftAP provisioning as fallback, not deleting it.
- [ ] Approve using current setup/claim token over BLE and keeping backend registration unchanged.
- [ ] Approve storing credentials in ESP32 NVS via existing `Preferences` keys.
- [ ] Approve adding a BLE dependency to PlatformIO if required.
- [ ] Approve adding unit-testable parser/state modules.
- [ ] Approve documentation updates for BLE UUIDs, payload format, and manual client usage.