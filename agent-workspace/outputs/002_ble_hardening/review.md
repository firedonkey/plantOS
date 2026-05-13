# Review

## Attempt 1

### Reviewer Agent

BLOCKED

## 1. Summary

The implementation follows much of the approved plan, and reported host/backend tests plus PlatformIO builds passed. However, the core duplicate-write hardening still has a race that can allow a second BLE payload to be accepted and later committed during the first payload’s commit window.

## 2. Findings

- Blocking: duplicate BLE writes can still slip through and commit.
  In `device/esp32/src/provisioning/ble_provisioning.cpp:152`, `takePendingResult()` clears `pending_result_ready_`. In `device/esp32/src/main.cpp:1758-1774`, writes are not disabled until after the pending result is taken and checked. During that window, `handleWrite()` at `ble_provisioning.cpp:172-205` can observe `pending_result_ready_ == false` and `accepting_writes_ == true`, queue a second payload, and that second payload can be processed before the scheduled reboot. This violates the approved plan’s idempotency and duplicate-write requirements.

## 3. Required Fixes Or Retest Requests

- Fix BLE pending-result consumption so accepting writes is disabled atomically with taking a valid pending payload, or otherwise keep the pending slot closed while commit is in progress.
- Add or run a targeted test for two valid BLE writes sent back-to-back before reboot, verifying only one commit occurs and the second write reports `busy` or `already_committed`.
- Rerun the ESP32 host provisioning test and firmware builds after the fix.

## 4. Residual Risk

Manual hardware validation is still needed for BLE advertising reconnects, timeout recovery, GPIO14 hold behavior, GPIO2 LED patterns, and real NVS save behavior. The accepted minimum persistence hardening still is not a true NVS transaction.

#### stdout

```
BLOCKED

## 1. Summary

The implementation follows much of the approved plan, and reported host/backend tests plus PlatformIO builds passed. However, the core duplicate-write hardening still has a race that can allow a second BLE payload to be accepted and later committed during the first payload’s commit window.

## 2. Findings

- Blocking: duplicate BLE writes can still slip through and commit.
  In `device/esp32/src/provisioning/ble_provisioning.cpp:152`, `takePendingResult()` clears `pending_result_ready_`. In `device/esp32/src/main.cpp:1758-1774`, writes are not disabled until after the pending result is taken and checked. During that window, `handleWrite()` at `ble_provisioning.cpp:172-205` can observe `pending_result_ready_ == false` and `accepting_writes_ == true`, queue a second payload, and that second payload can be processed before the scheduled reboot. This violates the approved plan’s idempotency and duplicate-write requirements.

## 3. Required Fixes Or Retest Requests

- Fix BLE pending-result consumption so accepting writes is disabled atomically with taking a valid pending payload, or otherwise keep the pending slot closed while commit is in progress.
- Add or run a targeted test for two valid BLE writes sent back-to-back before reboot, verifying only one commit occurs and the second write reports `busy` or `already_committed`.
- Rerun the ESP32 host provisioning test and firmware builds after the fix.

## 4. Residual Risk

Manual hardware validation is still needed for BLE advertising reconnects, timeout recovery, GPIO14 hold behavior, GPIO2 LED patterns, and real NVS save behavior. The accepted minimum persistence hardening still is not a true NVS transaction.
```

#### stderr

```
[truncated 164565 chars from the middle]
OpenAI Codex v0.128.0-alpha.1 (research preview)
--------
workdir: /Users/gary/plantOS
model: gpt-5.5
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 019e2283-02e2-7fe1-9005-46ed7d4e057c
--------
user
You are the Reviewer Agent for this repository.

Role constraints:
- Review the current repo state against the task, approved plan, coder output, tester output, and test report.
- Do not edit code.
- Decide whether the change is acceptable.

Your output is written to the active task output folder as `review.md`.

The first line must be exactly one of:
- APPROVED
- BLOCKED

Then include:

1. Summary
2. Findings
3. Required fixes or retest requests
4. Residual risk

Block when:
- the approved plan was not followed
- required tests are missing or failing
- the implementation is incomplete
- there is a clear correctness or regression risk

Repository root:
/Users/gary/plantOS

Current task id:
002_ble_hardening

Current task file:
/Users/gary/plantOS/agent-workspace/tasks/002_ble_hardening.md

Current task output folder:
/Users/gary/plantOS/agent-workspace/outputs/002_ble_hardening

Attempt: 1 of 3

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
- If no Wi-Fi credentials are saved, firmware starts BLE provisioning with `startBleProvisioningMode()`.
- GPIO14 long pre
...
claim_token;
  1957	  payload["node_role"] = "master";
  1958	  payload["display_name"] = "Master";
  1959	  payload["hardware_model"] = "esp32_master";
  1960	  payload["hardware_version"] = BOARD_NAME;
  1961	  payload["software_version"] = kSoftwareVersion;
  1962	  JsonObject capabilities = payload.createNestedObject("capabilities");
  1963	  capabilities["camera"] = false;
  1964	  capabilities["pump"] = true;
  1965	  capabilities["moisture_sensor"] = true;
  1966	  capabilities["light_control"] = true;
  1967	  capabilities["temperature_sensor"] = true;
  1968	  capabilities["humidity_sensor"] = true;
  1969	
  1970	  String body;
  1971	  serializeJson(payload, body);
  1972	
  1973	  HTTPClient http;
  1974	  http.setTimeout(kHttpTimeoutMs);
  1975	  const String url = platform_url + "/api/devices/register-provisioned";
  1976	  if (!http.begin(url)) {
  1977	    Serial.println("[provisioning] register request setup failed");
  1978	    return false;
  1979	  }
  1980	  http.addHeader("Content-Type", "application/json");
  1981	  const int status_code = http.POST(body);
  1982	  const String response_body = status_code > 0 ? http.getString() : http.errorToString(status_code);
  1983	  http.end();
  1984	
  1985	  if (status_code < 200 || status_code >= 300) {
  1986	    Serial.printf("[provisioning] registration failed HTTP %d: %s\n", status_code, response_body.c_str());
  1987	    return false;
  1988	  }
  1989	
  1990	  DynamicJsonDocument response(1024);
  1991	  const DeserializationError json_error = deserializeJson(response, response_body);
  1992	  if (json_error) {
  1993	    Serial.println("[provisioning] registration response JSON parse failed");
  1994	    return false;
  1995	  }
  1996	
  1997	  const int platform_device_id = response["platform_device_id"] | 0;
  1998	  const char* device_access_token = response["device_access_token"] | "";

2026-05-13T18:05:53.049261Z  WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt: prompt must be at most 128 characters path=/Users/gary/.codex/.tmp/plugins/plugins/build-ios-apps/.codex-plugin/plugin.json
2026-05-13T18:05:53.050667Z  WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt: maximum of 3 prompts is supported path=/Users/gary/.codex/.tmp/plugins/plugins/plugin-eval/.codex-plugin/plugin.json
2026-05-13T18:05:53.068222Z  WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt: maximum of 3 prompts is supported path=/Users/gary/.codex/.tmp/plugins/plugins/twilio-developer-kit/.codex-plugin/plugin.json
2026-05-13T18:05:53.068327Z  WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt: maximum of 3 prompts is supported path=/Users/gary/.codex/.tmp/plugins/plugins/openai-developers/.codex-plugin/plugin.json
2026-05-13T18:05:53.080853Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:05:53.080860Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:05:53.081692Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:05:53.081697Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:05:53.082670Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:05:53.082674Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:05:53.083018Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:05:53.083021Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:05:53.083353Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:05:53.083356Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:05:53.084268Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:05:53.084271Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
codex
BLOCKED

## 1. Summary

The implementation follows much of the approved plan, and reported host/backend tests plus PlatformIO builds passed. However, the core duplicate-write hardening still has a race that can allow a second BLE payload to be accepted and later committed during the first payload’s commit window.

## 2. Findings

- Blocking: duplicate BLE writes can still slip through and commit.
  In `device/esp32/src/provisioning/ble_provisioning.cpp:152`, `takePendingResult()` clears `pending_result_ready_`. In `device/esp32/src/main.cpp:1758-1774`, writes are not disabled until after the pending result is taken and checked. During that window, `handleWrite()` at `ble_provisioning.cpp:172-205` can observe `pending_result_ready_ == false` and `accepting_writes_ == true`, queue a second payload, and that second payload can be processed before the scheduled reboot. This violates the approved plan’s idempotency and duplicate-write requirements.

## 3. Required Fixes Or Retest Requests

- Fix BLE pending-result consumption so accepting writes is disabled atomically with taking a valid pending payload, or otherwise keep the pending slot closed while commit is in progress.
- Add or run a targeted test for two valid BLE writes sent back-to-back before reboot, verifying only one commit occurs and the second write reports `busy` or `already_committed`.
- Rerun the ESP32 host provisioning test and firmware builds after the fix.

## 4. Residual Risk

Manual hardware validation is still needed for BLE advertising reconnects, timeout recovery, GPIO14 hold behavior, GPIO2 LED patterns, and real NVS save behavior. The accepted minimum persistence hardening still is not a true NVS transaction.
tokens used
99,642
```

## Attempt 2

### Reviewer Agent

APPROVED

## 1. Summary

Attempt 2 resolves the prior blocking duplicate-write race. `takePendingResult()` now closes the BLE write gate while holding the pending-result critical section before clearing the pending slot, so a second valid write cannot be accepted during the commit window.

Reported verification passed for the ESP32 host provisioning test, PlatformIO firmware builds, `button-led-test`, backend pytest suite, and provision backend npm tests.

## 2. Findings

No blocking findings.

- `device/esp32/src/provisioning/ble_provisioning.cpp:152-169` disables accepting writes atomically when consuming a valid pending result.
- `device/esp32/src/provisioning/ble_provisioning.cpp:185-221` re-checks the write gate under lock before storing a parsed result and reports `busy` or `already_committed`.
- `device/esp32/tests_host/test_ble_provisioning_payload.cpp:371-398` covers the duplicate valid write gate behavior requested by the previous review.

## 3. Required Fixes Or Retest Requests

No required code fixes.

Before production rollout, complete the remaining manual hardware validation from the approved plan: real BLE duplicate writes, disconnect/reconnect advertising, timeout recovery, GPIO14 provisioning/reset behavior, GPIO2 LED patterns, NVS save behavior, Wi-Fi reconnect, and backend heartbeat.

## 4. Residual Risk

The duplicate-write regression is covered through host-testable helper logic rather than real NimBLE callback interleaving. BLE status JSON behavior, hardware radio interactions, and NVS partial-write behavior still depend on manual ESP32-S3 validation. The persistence hardening remains the approved minimum write-result checking, not a true multi-key NVS transaction.

#### stdout

```
APPROVED

## 1. Summary

Attempt 2 resolves the prior blocking duplicate-write race. `takePendingResult()` now closes the BLE write gate while holding the pending-result critical section before clearing the pending slot, so a second valid write cannot be accepted during the commit window.

Reported verification passed for the ESP32 host provisioning test, PlatformIO firmware builds, `button-led-test`, backend pytest suite, and provision backend npm tests.

## 2. Findings

No blocking findings.

- `device/esp32/src/provisioning/ble_provisioning.cpp:152-169` disables accepting writes atomically when consuming a valid pending result.
- `device/esp32/src/provisioning/ble_provisioning.cpp:185-221` re-checks the write gate under lock before storing a parsed result and reports `busy` or `already_committed`.
- `device/esp32/tests_host/test_ble_provisioning_payload.cpp:371-398` covers the duplicate valid write gate behavior requested by the previous review.

## 3. Required Fixes Or Retest Requests

No required code fixes.

Before production rollout, complete the remaining manual hardware validation from the approved plan: real BLE duplicate writes, disconnect/reconnect advertising, timeout recovery, GPIO14 provisioning/reset behavior, GPIO2 LED patterns, NVS save behavior, Wi-Fi reconnect, and backend heartbeat.

## 4. Residual Risk

The duplicate-write regression is covered through host-testable helper logic rather than real NimBLE callback interleaving. BLE status JSON behavior, hardware radio interactions, and NVS partial-write behavior still depend on manual ESP32-S3 validation. The persistence hardening remains the approved minimum write-result checking, not a true multi-key NVS transaction.
```

#### stderr

```
[truncated 153743 chars from the middle]
OpenAI Codex v0.128.0-alpha.1 (research preview)
--------
workdir: /Users/gary/plantOS
model: gpt-5.5
provider: openai
approval: never
sandbox: read-only
reasoning effort: high
reasoning summaries: none
session id: 019e228a-0a1f-7e73-8430-d3750b0502d3
--------
user
You are the Reviewer Agent for this repository.

Role constraints:
- Review the current repo state against the task, approved plan, coder output, tester output, and test report.
- Do not edit code.
- Decide whether the change is acceptable.

Your output is written to the active task output folder as `review.md`.

The first line must be exactly one of:
- APPROVED
- BLOCKED

Then include:

1. Summary
2. Findings
3. Required fixes or retest requests
4. Residual risk

Block when:
- the approved plan was not followed
- required tests are missing or failing
- the implementation is incomplete
- there is a clear correctness or regression risk

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
- If no Wi-Fi credentials are saved, firmware starts BLE provisioning with `startBleProvisioningMode()`.
- GPIO14 long pre
...
ayload.cpp:65:      return "FALLBACK_SOFTAP";
device/esp32/src/provisioning/provisioning_payload.cpp:66:    case ProvisioningState::FACTORY_RESET_PENDING:
device/esp32/src/provisioning/provisioning_payload.cpp:67:      return "FACTORY_RESET_PENDING";
device/esp32/src/provisioning/provisioning_payload.cpp:200:  return ProvisioningState::PROVISIONING_COMMITTING;
device/esp32/src/provisioning/ble_provisioning.h:39:  void setAcceptingWrites(bool accepting);
device/esp32/src/provisioning/ble_provisioning.cpp:178:void BleProvisioningService::setAcceptingWrites(bool accepting) {
device/esp32/src/provisioning/provisioning_payload.h:18:  PROVISIONING_COMMITTING,
device/esp32/src/provisioning/provisioning_payload.h:20:  BACKEND_REGISTERING,
device/esp32/src/provisioning/provisioning_payload.h:23:  FALLBACK_SOFTAP,
device/esp32/src/provisioning/provisioning_payload.h:24:  FACTORY_RESET_PENDING,
device/esp32/src/system/status_led.h:5:enum class StatusLedMode {
device/esp32/src/system/status_led.h:21:  void set_mode(StatusLedMode mode);
device/esp32/src/system/status_led.h:31:  StatusLedMode mode_;
device/esp32/src/system/status_led.cpp:9:      mode_(StatusLedMode::kBooting),
device/esp32/src/system/status_led.cpp:18:void StatusLed::set_mode(StatusLedMode mode) {
device/esp32/src/system/status_led.cpp:39:    case StatusLedMode::kOff:
device/esp32/src/system/status_led.cpp:42:    case StatusLedMode::kNormal:
device/esp32/src/system/status_led.cpp:45:    case StatusLedMode::kProvisioning:
device/esp32/src/system/status_led.cpp:48:    case StatusLedMode::kSleepPending:
device/esp32/src/system/status_led.cpp:51:    case StatusLedMode::kError:
device/esp32/src/system/status_led.cpp:54:    case StatusLedMode::kFallback:
device/esp32/src/system/status_led.cpp:60:    case StatusLedMode::kFactoryReset:
device/esp32/src/system/status_led.cpp:63:    case StatusLedMode::kBooting:

2026-05-13T18:12:35.422270Z  WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt: prompt must be at most 128 characters path=/Users/gary/.codex/.tmp/plugins/plugins/build-ios-apps/.codex-plugin/plugin.json
2026-05-13T18:12:35.423798Z  WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt: maximum of 3 prompts is supported path=/Users/gary/.codex/.tmp/plugins/plugins/plugin-eval/.codex-plugin/plugin.json
2026-05-13T18:12:35.438153Z  WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt: maximum of 3 prompts is supported path=/Users/gary/.codex/.tmp/plugins/plugins/twilio-developer-kit/.codex-plugin/plugin.json
2026-05-13T18:12:35.438276Z  WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt: maximum of 3 prompts is supported path=/Users/gary/.codex/.tmp/plugins/plugins/openai-developers/.codex-plugin/plugin.json
2026-05-13T18:12:35.450932Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:12:35.450944Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:12:35.451726Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:12:35.451729Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:12:35.452629Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:12:35.452634Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:12:35.453001Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:12:35.453005Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:12:35.453360Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:12:35.453363Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
2026-05-13T18:12:35.454388Z  WARN codex_core_skills::loader: ignoring interface.icon_small: icon path must not contain '..'
2026-05-13T18:12:35.454391Z  WARN codex_core_skills::loader: ignoring interface.icon_large: icon path must not contain '..'
codex
APPROVED

## 1. Summary

Attempt 2 resolves the prior blocking duplicate-write race. `takePendingResult()` now closes the BLE write gate while holding the pending-result critical section before clearing the pending slot, so a second valid write cannot be accepted during the commit window.

Reported verification passed for the ESP32 host provisioning test, PlatformIO firmware builds, `button-led-test`, backend pytest suite, and provision backend npm tests.

## 2. Findings

No blocking findings.

- `device/esp32/src/provisioning/ble_provisioning.cpp:152-169` disables accepting writes atomically when consuming a valid pending result.
- `device/esp32/src/provisioning/ble_provisioning.cpp:185-221` re-checks the write gate under lock before storing a parsed result and reports `busy` or `already_committed`.
- `device/esp32/tests_host/test_ble_provisioning_payload.cpp:371-398` covers the duplicate valid write gate behavior requested by the previous review.

## 3. Required Fixes Or Retest Requests

No required code fixes.

Before production rollout, complete the remaining manual hardware validation from the approved plan: real BLE duplicate writes, disconnect/reconnect advertising, timeout recovery, GPIO14 provisioning/reset behavior, GPIO2 LED patterns, NVS save behavior, Wi-Fi reconnect, and backend heartbeat.

## 4. Residual Risk

The duplicate-write regression is covered through host-testable helper logic rather than real NimBLE callback interleaving. BLE status JSON behavior, hardware radio interactions, and NVS partial-write behavior still depend on manual ESP32-S3 validation. The persistence hardening remains the approved minimum write-result checking, not a true multi-key NVS transaction.
tokens used
49,178
```

