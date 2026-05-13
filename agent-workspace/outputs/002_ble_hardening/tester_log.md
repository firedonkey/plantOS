# 1. Test changes made

- Tightened `test_duplicate_valid_write_gate()` in `test_ble_provisioning_payload.cpp` to model the reviewer-blocking case: a valid pending write reports `busy`, taking the valid pending result closes the write gate, the next write during `PROVISIONING_COMMITTING` reports `busy`, and writes after `PROVISIONING_SUCCESS` report `already_committed`.
- Kept existing host coverage for invalid writes leaving the write gate open for retry.
- Kept existing host coverage for parser aliases, trimmed accepted fields, exact maximum field lengths, state names, timeout transitions, and provisioning error codes.

# 2. Files changed

- `device/esp32/tests_host/test_ble_provisioning_payload.cpp`
- `agent-workspace/outputs/002_ble_hardening/tester_log.md`

# 3. Recommended commands to verify

- `./.venv/bin/pytest -q platform/backend/tests/test_esp32_ble_provisioning_host.py` - passed.
- `git diff --check -- device/esp32/tests_host/test_ble_provisioning_payload.cpp` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-s3-devkitc-1` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-local` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-gcp` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e button-led-test` - passed.

# 4. Remaining test gaps

- The duplicate-write regression is covered through the host-testable write-gate helper, not by real NimBLE callback interleaving on hardware.
- BLE status characteristic JSON, disconnect/reconnect advertising, and timeout recovery still require hardware or a dedicated NimBLE test seam.
- GPIO14 5-second provisioning entry, GPIO14 10-second factory reset, and GPIO2 LED patterns were build-checked only; manual hardware validation is still required.
- NVS save-failure and reset-during-save behavior are not host-tested because `Preferences` is hardware/framework-owned and no production test seam was added.
- Existing Wi-Fi reconnect and backend heartbeat regression coverage remains manual for this ESP32 firmware path.
# 1. Test changes made

- Tightened `test_duplicate_valid_write_gate()` in `test_ble_provisioning_payload.cpp` to model the reviewer-blocking case: a valid pending write reports `busy`, taking the valid pending result closes the write gate, the next write during `PROVISIONING_COMMITTING` reports `busy`, and writes after `PROVISIONING_SUCCESS` report `already_committed`.
- Kept existing host coverage for invalid writes leaving the write gate open for retry.
- Kept existing host coverage for parser aliases, trimmed accepted fields, exact maximum field lengths, state names, timeout transitions, and provisioning error codes.

# 2. Files changed

- `device/esp32/tests_host/test_ble_provisioning_payload.cpp`
- `agent-workspace/outputs/002_ble_hardening/tester_log.md`

# 3. Recommended commands to verify

- `./.venv/bin/pytest -q platform/backend/tests/test_esp32_ble_provisioning_host.py` - passed.
- `git diff --check -- device/esp32/tests_host/test_ble_provisioning_payload.cpp` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-s3-devkitc-1` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-local` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-gcp` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e button-led-test` - passed.

# 4. Remaining test gaps

- The duplicate-write regression is covered through the host-testable write-gate helper, not by real NimBLE callback interleaving on hardware.
- BLE status characteristic JSON, disconnect/reconnect advertising, and timeout recovery still require hardware or a dedicated NimBLE test seam.
- GPIO14 5-second provisioning entry, GPIO14 10-second factory reset, and GPIO2 LED patterns were build-checked only; manual hardware validation is still required.
- NVS save-failure and reset-during-save behavior are not host-tested because `Preferences` is hardware/framework-owned and no production test seam was added.
- Existing Wi-Fi reconnect and backend heartbeat regression coverage remains manual for this ESP32 firmware path.

#### stdout

```
# 1. Test changes made

- Tightened `test_duplicate_valid_write_gate()` in `test_ble_provisioning_payload.cpp` to model the reviewer-blocking case: a valid pending write reports `busy`, taking the valid pending result closes the write gate, the next write during `PROVISIONING_COMMITTING` reports `busy`, and writes after `PROVISIONING_SUCCESS` report `already_committed`.
- Kept existing host coverage for invalid writes leaving the write gate open for retry.
- Kept existing host coverage for parser aliases, trimmed accepted fields, exact maximum field lengths, state names, timeout transitions, and provisioning error codes.

# 2. Files changed

- `device/esp32/tests_host/test_ble_provisioning_payload.cpp`
- `agent-workspace/outputs/002_ble_hardening/tester_log.md`

# 3. Recommended commands to verify

- `./.venv/bin/pytest -q platform/backend/tests/test_esp32_ble_provisioning_host.py` - passed.
- `git diff --check -- device/esp32/tests_host/test_ble_provisioning_payload.cpp` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-s3-devkitc-1` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-local` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-gcp` - passed.
- `cd device/esp32 && PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e button-led-test` - passed.

# 4. Remaining test gaps

- The duplicate-write regression is covered through the host-testable write-gate helper, not by real NimBLE callback interleaving on hardware.
- BLE status characteristic JSON, disconnect/reconnect advertising, and timeout recovery still require hardware or a dedicated NimBLE test seam.
- GPIO14 5-second provisioning entry, GPIO14 10-second factory reset, and GPIO2 LED patterns were build-checked only; manual hardware validation is still required.
- NVS save-failure and reset-during-save behavior are not host-tested because `Preferences` is hardware/framework-owned and no production test seam was added.
- Existing Wi-Fi reconnect and backend heartbeat regression coverage remains manual for this ESP32 firmware path.
```

#### stderr

```
[truncated 283538 chars from the middle]
OpenAI Codex v0.128.0-alpha.1 (research preview)
--------
workdir: /Users/gary/plantOS
model: gpt-5.5
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, /Users/gary/.codex/memories] (network access enabled)
reasoning effort: high
reasoning summaries: none
session id: 019e2288-187f-7491-b0ac-f3690fde340b
--------
user
You are the Tester Agent for this repository.

Role constraints:
- Add or update tests needed for the approved plan.
- You may edit test files, test helpers, and test fixtures.
- Do not edit production code unless the pipeline owner explicitly instructs otherwise.
- Run relevant tests if useful, but the wrapper script will also run detected project test commands and write the canonical report.
- Document what was tested and what was not.

Your output is written to the active task output folder as `tester_log.md`.

Required output structure:

1. Test changes made
2. Files changed
3. Recommended commands to verify
4. Remaining test gaps

Keep the output factual.

Repository root:
/Users/gary/plantOS

Current task id:
002_ble_hardening

Current task file:
/Users/gary/plantOS/agent-workspace/tasks/002_ble_hardening.md

Current task output folder:
/Users/gary/plantOS/agent-workspace/outputs/002_ble_hardening

Attempt: 2 of 3

Task:
```md
# BLE Hardening

Feature request: BLE onboarding hardening + fallback cleanup for PlantLab ESP32 master node.

Use the existing 4-agent workflow:
Planner → wait for my approval → Coder → Tester → Reviewer.

Planner Agent only:
- Study the current repo first.
- Do not edit production code.
- Do not implement anything yet.
- Create only agent-workspace/plan.md.
- The plan should be detailed enough that Coder can implement it later without redesigning.

Goal:
Improve the BLE onboarding flow so it is safer, more reliable, and cleaner, while preserving existing working behavior.

Main areas to design:

1. BLE onboarding hardening
- Review current BLE provisioning/onboarding flow.
- Identify race conditions, timeout issues, reconnect issues, duplicate onboarding attempts, and partial credential save problems.
- Define a safer provisioning state machine.
- Make failure handling clear and recoverable.
- Make onboarding idempotent where possible.
- Prevent accidental overwriting of valid credentials unless user intentionally enters provisioning mode.

2. Credential and token safety
- Never log Wi-Fi password.
- Never log full device token.
- Mask sensitive values in serial logs.
- Decide when credentials should be saved.
- Avoid saving partial or invalid onboarding data.
- Prefer atomic save/commit behavior if possible.
- Define how to clear old credentials safely.

3. Fallback cleanup
- Review existing fallback behavior such as SoftAP, saved Wi-Fi fallback, BLE fallback, reset button behavior, or any legacy provisioning path.
- Decide which fallback paths should remain.
- Decide which fallback paths should be removed, simplified, or gated behind an explicit user action.
- Avoid automatic fallback loops that confuse onboarding.
- Make fallback behavior deterministic and easy to debug.

4. Button and LED behavior
- Use GPIO14 provisioning button.
- Use GPIO2 status LED.
- Define short press / long press behavior if needed.
- Define LED states for:
  - normal boot
  - BLE provisioning active
  - Wi-Fi connecting
  - backend registration/heartbeat success
  - provisioning failed
  - fallback mode
  - factory reset / credential clear

5. Wi-Fi + BLE interaction
- Review whether BLE onboarding conflicts with Wi-Fi connection logic.
- Decide when Wi-Fi should be active or disabled during BLE provisioning.
- Prevent BLE and Wi-Fi state machines from fighting each other.
- Define safe transitions after BLE credentials are received.

6. Backend/device-token flow
- Existing backend uses PlantLab device tokens.
- Do not break current backend heartbeat/registration.
- Define how the device token should be validated/stored/used.
- If backend changes are unnecessary, explicitly say no backend changes are needed.

7. Testing plan
Planner should include test cases for:
- successful BLE onboarding
- invalid payload
- missing SSID
- missing password
- missing device token
- disconnect during onboarding
- timeout during onboarding
- repeated provisioning attempts
- reboot during provisioning
- existing valid credentials should not be overwritten accidentally
- fallback path behavior
- no secret logging
- existing Wi-Fi/backend heartbeat still works

8. Review risks
Planner should call out:
- high-risk files
- expected code modules to change
- areas that need careful manual testing on hardware
- assumptions that Coder should not violate

Constraints:
- Board: ESP32-S3-DevKitC-1-N32R16V.
- Status LED: GPIO2.
- Provisioning button: GPIO14.
- BLE onboarding should be additive and safe.
- Do not remove working behavior unless the plan clearly explains why.
- Do not redesign unrelated firmware modules.
- Keep implementation small and staged.
- Prefer testable parser/state logic that can run without real BLE hardware.

Planner output format:
Write agent-workspace/plan.md with these sections:

1. Current Flow Summary
2. Problems / Risks Found
3. Proposed BLE Onboarding State Machine
4. Credential + Token Storage Rules
5. Fallback Cleanup Plan
6. Button + LED Behavior
7. Wi-Fi/BLE Coordination Rules
8. Backend Impact
9. Files Likely To Change
10. Implementation Steps For Coder
11. Test Plan
12. Manual Hardware Validation Checklist
13. Non-goals
14. Open Questions / Assumptions

Stop after writing the plan.
Do not run Coder yet.
```

Approved plan:
```md
# 1. Current Flow Summary

The ESP32 master firmware already has BLE onboarding in `device/esp32/src/provisioning/ble_provisioning.*`, BLE payload parsing in `device/esp32/src/provisioning/provisioning_payload.*`, and integration in `device/esp32/src/main.cpp`.

Current boot behavior:
- `setup()` calls `loadConfig()`.
- If `hasWifiCredentials()` is true, firmware attempts `connectToWiFi()`.
- If no Wi-
...
ult.ok);
-+  assert(result.payload.plantlab_token == "claim-token");
-+}
-+
-+void test_trims_accepted_fields() {
-+  const char json[] =
-+      "{\"ssid\":\"  HomeWiFi  \",\"password\":\"  wifi-password  \","
-+      "\"plantlab_token\":\"  claim-token  \","
-+      "\"platform_url\":\"  https://platform.example  \","
-+      "\"backend_url\":\"  https://provisioning.example  \"}";
-+  const plantlab::ProvisioningParseResult result =
-+      plantlab::parseBleProvisioningPayload(json, strlen(json));
-+  assert(result.ok);
-+  assert(result.payload.ssid == "HomeWiFi");
-+  assert(result.payload.password == "wifi-password");
-+  assert(result.payload.plantlab_token == "claim-token");
-+  assert(result.payload.platform_url == "https://platform.example");
-+  assert(result.payload.backend_url == "https://provisioning.example");
-+}
-+
- void test_missing_fields() {
-   const char missing_ssid[] =
-       "{\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
-@@ -144,6 +171,54 @@
- }
- 
- void test_length_limits() {
-+  const std::string max_ssid(plantlab::kProvisioningMaxSsidLength, 's');
-+  const std::string max_ssid_json =
-+      "{\"ssid\":\"" + max_ssid +
-+      "\",\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
-+      "\"platform_url\":\"https://platform.example\"}";
-+  const plantlab::ProvisioningParseResult max_ssid_result =
-+      plantlab::parseBleProvisioningPayload(max_ssid_json.c_str(), max_ssid_json.length());
-+  assert(max_ssid_result.ok);
-+  assert(max_ssid_result.payload.ssid.length() == plantlab::kProvisioningMaxSsidLength);
-+
-+  const std::string max_password(plantlab::kProvisioningMaxPasswordLength, 'p');
-+  const std::string max_password_json =
-+      "{\"ssid\":\"HomeWiFi\",\"password\":\"" + max_password +
-+      "\",\"plantlab_token\":\"token\",\"platform_url\":\"https://platform.example\"}";
-+  const plantlab::ProvisioningParseResult max_password_result =
-+      plantlab::parseBleProvisioningPayload(max_password_json.c_str(), max_password_json.length());
-+  assert(max_password_result.ok);
-+  assert(max_password_result.payload.password.length() == plantlab::kProvisioningMaxPasswordLength);
-+
-+  const std::string max_token(plantlab::kProvisioningMaxTokenLength, 't');
-+  const std::string max_token_json =
-+      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"" +
-+      max_token + "\",\"platform_url\":\"https://platform.example\"}";
-+  const plantlab::ProvisioningParseResult max_token_result =
-+      plantlab::parseBleProvisioningPayload(max_token_json.c_str(), max_token_json.length());
-+  assert(max_token_result.ok);
-+  assert(max_token_result.payload.plantlab_token.length() == plantlab::kProvisioningMaxTokenLength);
-+
-+  const std::string max_platform_url(plantlab::kProvisioningMaxUrlLength, 'u');
-+  const std::string max_platform_url_json =
-+      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
-+      "\"platform_url\":\"" + max_platform_url + "\"}";
-+  const plantlab::ProvisioningParseResult max_platform_url_result =
-+      plantlab::parseBleProvisioningPayload(
-+          max_platform_url_json.c_str(),
-+          max_platform_url_json.length());
-+  assert(max_platform_url_result.ok);
-+  assert(max_platform_url_result.payload.platform_url.length() == plantlab::kProvisioningMaxUrlLength);
-+
-+  const std::string max_backend_url(plantlab::kProvisioningMaxUrlLength, 'b');
-+  const std::string max_backend_url_json =
-+      "{\"ssid\":\"HomeWiFi\",\"password\":\"wifi-password\",\"plantlab_token\":\"token\","
-+      "\"platform_url\":\"https://platform.example\",\"backend_url\":\"" + max_backend_url + "\"}";
-+  const plantlab::ProvisioningParseResult max_backend_url_result =
-+      plantlab::parseBleProvisioningPayload(max_backend_url_json.c_str(), max_backend_url_json.length());
-+  assert(max_backend_url_result.ok);
-+  assert(max_backend_url_result.payload.backend_url.length() == plantlab::kProvisioningMaxUrlLength);
-+
-   const std::string long_ssid(33, 'a');
-   const std::string ssid_json =
-       "{\"ssid\":\"" + long_ssid +
-@@ -300,6 +375,8 @@
-   test_alias_payload();
-   test_primary_fields_take_precedence_over_aliases();
-   test_claim_token_alias_payload();
-+  test_claim_token_used_when_setup_alias_is_blank();
-+  test_trims_accepted_fields();
-   test_missing_fields();
-   test_platform_url_fallback();
-   test_invalid_json_and_malformed_payload();
-
-tokens used
-65,504
-```
-
-## Attempt 2
-
-### Tester Agent
-
diff --git a/device/esp32/tests_host/test_ble_provisioning_payload.cpp b/device/esp32/tests_host/test_ble_provisioning_payload.cpp
index 39fd8ced81da8b21e16b324098fddcc82bf689a5..f12d824af314c5af08e80e3d81c280a17e87df59
--- a/device/esp32/tests_host/test_ble_provisioning_payload.cpp
+++ b/device/esp32/tests_host/test_ble_provisioning_payload.cpp
@@ -373,15 +373,22 @@
   bool has_pending_result = true;
   const bool valid_result = true;
 
+  assert(plantlab::provisioningWriteRejectionError(
+             plantlab::ProvisioningState::PROVISIONING_BLE,
+             has_pending_result,
+             accepting_writes) == plantlab::ProvisioningParseError::kBusy);
   assert(plantlab::provisioningShouldStopAcceptingWritesOnTake(
       has_pending_result,
       valid_result,
       accepting_writes));
 
+  // Model the first valid payload being consumed by the main loop: the gate
+  // closes before the pending slot is cleared, so a second valid write is
+  // rejected during commit and after success.
   accepting_writes = false;
   has_pending_result = false;
   assert(plantlab::provisioningWriteRejectionError(
-             plantlab::ProvisioningState::PROVISIONING_BLE,
+             plantlab::ProvisioningState::PROVISIONING_COMMITTING,
              has_pending_result,
              accepting_writes) == plantlab::ProvisioningParseError::kBusy);
   assert(plantlab::provisioningWriteRejectionError(

tokens used
55,011
```

