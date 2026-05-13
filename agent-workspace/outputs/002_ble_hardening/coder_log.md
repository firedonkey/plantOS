# Coder Log

## Attempt 2

## 1. Summary of code changes

- Fixed the reviewer-blocking duplicate BLE write race by closing the BLE write gate inside `BleProvisioningService::takePendingResult()` while still holding the pending-result critical section.
- Kept invalid BLE payload behavior open for retry: invalid pending results are still consumed without disabling further writes.
- Added host-testable provisioning write-gate helpers for the duplicate-write decision path.
- Updated BLE write handling to use the shared write-gate helper for pending, busy, and already-committed responses.
- Tightened `setAcceptingWrites()` so the accepting flag is updated under the same pending-result lock used by BLE callbacks.
- Added targeted host coverage for the back-to-back valid write gate: first valid pending result closes writes, the next write reports `busy` during provisioning/commit and `already_committed` after success.

Verification run:
- `./.venv/bin/pytest -q platform/backend/tests/test_esp32_ble_provisioning_host.py` passed.
- `PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-s3-devkitc-1` passed.
- `PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-local` passed.
- `PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e esp32-gcp` passed.
- `PLATFORMIO_CORE_DIR=/tmp/plantos-platformio ../../.venv/bin/pio run -e button-led-test` passed.
- `git diff --check -- device/esp32/src/provisioning/ble_provisioning.cpp device/esp32/src/provisioning/provisioning_payload.h device/esp32/src/provisioning/provisioning_payload.cpp device/esp32/tests_host/test_ble_provisioning_payload.cpp` passed.

## 2. Files changed

- `device/esp32/src/provisioning/ble_provisioning.cpp`
- `device/esp32/src/provisioning/provisioning_payload.h`
- `device/esp32/src/provisioning/provisioning_payload.cpp`
- `device/esp32/tests_host/test_ble_provisioning_payload.cpp`

## 3. Deviations from plan, if any

- No new deviations from the approved plan.
- This pass only addressed the reviewer-blocking duplicate-write race and added the targeted host coverage requested by review.

## 4. Risks or follow-up for Tester/Reviewer

- Reviewer should re-check the BLE pending-result critical section around `takePendingResult()` and `handleWrite()`.
- Manual hardware validation is still required for real BLE duplicate writes, disconnect/reconnect advertising, timeout recovery, GPIO14 hold behavior, GPIO2 LED patterns, and NVS save behavior.
- `Preferences` still has no true multi-key transaction; this remains the approved minimum persistence hardening rather than atomic NVS commit support.
- PlatformIO builds still emit existing ArduinoJson deprecation warnings in `registerProvisionedDevice()`; unchanged by this pass.
# Coder Log

## Attempt 2

## 1. Summary of code changes

- Fixed the reviewer-blocking duplicate BLE write race by closing the BLE write gate inside `BleProvisioningService::takePendingResult()` while still holding the pending-result critical section.
- Kept invalid BLE payload behavior open for retry: invalid pending results are still consumed without disabling further writes.
- Added host-testable provisioning write-gate helpers for the duplicate-write decision path.
- Updated BLE write handling to use the shared write-gate helper for pending, busy, and already-committed responses.
- Tightened `setAcceptingWrites()` so the accepting flag is updated under the same pending-result lock used by BLE callbacks.
- Added targeted host coverage for the back-to-back valid write gate.

## 2. Files changed

- `device/esp32/src/provisioning/ble_provisioning.cpp`
- `device/esp32/src/provisioning/provisioning_payload.h`
- `device/esp32/src/provisioning/provisioning_payload.cpp`
- `device/esp32/tests_host/test_ble_provisioning_payload.cpp`

## 3. Deviations from plan, if any

- No new deviations from the approved plan.
- This pass only addressed the reviewer-blocking duplicate-write race and added the targeted host coverage requested by review.

## 4. Risks or follow-up for Tester/Reviewer

- Reviewer should re-check the BLE pending-result critical section around `takePendingResult()` and `handleWrite()`.
- Manual hardware validation is still required for real BLE duplicate writes, disconnect/reconnect advertising, timeout recovery, GPIO14 hold behavior, GPIO2 LED patterns, and NVS save behavior.
- `Preferences` still has no true multi-key transaction.
- PlatformIO builds still emit existing ArduinoJson deprecation warnings.

#### stdout

```
# Coder Log

## Attempt 2

## 1. Summary of code changes

- Fixed the reviewer-blocking duplicate BLE write race by closing the BLE write gate inside `BleProvisioningService::takePendingResult()` while still holding the pending-result critical section.
- Kept invalid BLE payload behavior open for retry: invalid pending results are still consumed without disabling further writes.
- Added host-testable provisioning write-gate helpers for the duplicate-write decision path.
- Updated BLE write handling to use the shared write-gate helper for pending, busy, and already-committed responses.
- Tightened `setAcceptingWrites()` so the accepting flag is updated under the same pending-result lock used by BLE callbacks.
- Added targeted host coverage for the back-to-back valid write gate.

## 2. Files changed

- `device/esp32/src/provisioning/ble_provisioning.cpp`
- `device/esp32/src/provisioning/provisioning_payload.h`
- `device/esp32/src/provisioning/provisioning_payload.cpp`
- `device/esp32/tests_host/test_ble_provisioning_payload.cpp`

## 3. Deviations from plan, if any

- No new deviations from the approved plan.
- This pass only addressed the reviewer-blocking duplicate-write race and added the targeted host coverage requested by review.

## 4. Risks or follow-up for Tester/Reviewer

- Reviewer should re-check the BLE pending-result critical section around `takePendingResult()` and `handleWrite()`.
- Manual hardware validation is still required for real BLE duplicate writes, disconnect/reconnect advertising, timeout recovery, GPIO14 hold behavior, GPIO2 LED patterns, and NVS save behavior.
- `Preferences` still has no true multi-key transaction.
- PlatformIO builds still emit existing ArduinoJson deprecation warnings.
```

#### stderr

```
[truncated 507662 chars from the middle]
OpenAI Codex v0.128.0-alpha.1 (research preview)
--------
workdir: /Users/gary/plantOS
model: gpt-5.5
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR, /Users/gary/.codex/memories] (network access enabled)
reasoning effort: high
reasoning summaries: none
session id: 019e2284-a2bc-73a1-aa22-037b84d79d81
--------
user
You are the Coder Agent for this repository.

Role constraints:
- Implement only the approved plan.
- Do not expand scope.
- Do not rewrite unrelated systems.
- Do not add production features not justified by the approved plan.
- Prefer small, reversible changes.
- You may update docs only when directly required by the approved plan.
- Do not add or rewrite tests unless the approved plan explicitly requires production-side test fixtures or helpers. The Tester Agent owns normal test updates.

Your output is written to the active task output folder as `coder_log.md`.

Required output structure:

1. Summary of code changes
2. Files changed
3. Deviations from plan, if any
4. Risks or follow-up for Tester/Reviewer

Keep the output concrete and implementation-focused.

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
- `setup()` cal
...
    accepting_writes_ = false;
+    status_changed = true;
+  }
   pending_result_ready_ = false;
   pending_result_ = ProvisioningParseResult{};
   portEXIT_CRITICAL(&pending_lock_);
+  if (status_changed) {
+    publishStatus(true);
+  }
   return result;
 }
 
@@ -165,7 +176,9 @@
 }
 
 void BleProvisioningService::setAcceptingWrites(bool accepting) {
+  portENTER_CRITICAL(&pending_lock_);
   accepting_writes_ = accepting;
+  portEXIT_CRITICAL(&pending_lock_);
   publishStatus(true);
 }
 
@@ -175,15 +188,8 @@
   const bool accepting = accepting_writes_;
   portEXIT_CRITICAL(&pending_lock_);
 
-  if (pending) {
-    setStatus(state_, ProvisioningParseError::kBusy);
-    return;
-  }
-  if (!accepting) {
-    const ProvisioningParseError error =
-        state_ == ProvisioningState::PROVISIONING_SUCCESS
-            ? ProvisioningParseError::kAlreadyCommitted
-            : ProvisioningParseError::kBusy;
+  ProvisioningParseError error = provisioningWriteRejectionError(state_, pending, accepting);
+  if (error != ProvisioningParseError::kNone) {
     setStatus(state_, error);
     return;
   }
@@ -194,18 +200,20 @@
       fallback_platform_url_.c_str());
 
   portENTER_CRITICAL(&pending_lock_);
-  if (!pending_result_ready_ && accepting_writes_) {
+  error = provisioningWriteRejectionError(state_, pending_result_ready_, accepting_writes_);
+  if (error == ProvisioningParseError::kNone) {
     pending_result_ = result;
     pending_result_ready_ = true;
     result = pending_result_;
   } else {
     result = ProvisioningParseResult{};
-    result.error = ProvisioningParseError::kBusy;
+    result.error = error;
   }
   portEXIT_CRITICAL(&pending_lock_);
 
-  if (result.error == ProvisioningParseError::kBusy) {
-    setStatus(state_, ProvisioningParseError::kBusy);
+  if (result.error == ProvisioningParseError::kBusy ||
+      result.error == ProvisioningParseError::kAlreadyCommitted) {
+    setStatus(state_, result.error);
     return;
   }
   if (!result.ok) {
diff --git a/device/esp32/src/provisioning/provisioning_payload.cpp b/device/esp32/src/provisioning/provisioning_payload.cpp
index 2f392f1c341059934700f39ceeec51150ca476b0..5f796b27f05e2aed5e91267a51a90a6f6b66147c
--- a/device/esp32/src/provisioning/provisioning_payload.cpp
+++ b/device/esp32/src/provisioning/provisioning_payload.cpp
@@ -209,4 +209,26 @@
                                      : ProvisioningState::PROVISIONING_FAILED;
 }
 
+ProvisioningParseError provisioningWriteRejectionError(
+    ProvisioningState state,
+    bool has_pending_result,
+    bool accepting_writes) {
+  if (has_pending_result) {
+    return ProvisioningParseError::kBusy;
+  }
+  if (!accepting_writes) {
+    return state == ProvisioningState::PROVISIONING_SUCCESS
+               ? ProvisioningParseError::kAlreadyCommitted
+               : ProvisioningParseError::kBusy;
+  }
+  return ProvisioningParseError::kNone;
+}
+
+bool provisioningShouldStopAcceptingWritesOnTake(
+    bool has_pending_result,
+    bool result_ok,
+    bool accepting_writes) {
+  return has_pending_result && result_ok && accepting_writes;
+}
+
 }  // namespace plantlab
diff --git a/device/esp32/src/provisioning/provisioning_payload.h b/device/esp32/src/provisioning/provisioning_payload.h
index 64bd5118b807904f541b56aa7e8d64186a92db56..0100c48e710b53ec0395da7130aad3f2e9b554b5
--- a/device/esp32/src/provisioning/provisioning_payload.h
+++ b/device/esp32/src/provisioning/provisioning_payload.h
@@ -72,5 +72,13 @@
 ProvisioningState provisioningStateAfterValidPayload();
 ProvisioningState provisioningStateAfterInvalidPayload();
 ProvisioningState provisioningStateAfterTimeout(bool has_previous_runtime_config);
+ProvisioningParseError provisioningWriteRejectionError(
+    ProvisioningState state,
+    bool has_pending_result,
+    bool accepting_writes);
+bool provisioningShouldStopAcceptingWritesOnTake(
+    bool has_pending_result,
+    bool result_ok,
+    bool accepting_writes);
 
 }  // namespace plantlab
diff --git a/device/esp32/tests_host/test_ble_provisioning_payload.cpp b/device/esp32/tests_host/test_ble_provisioning_payload.cpp
index fc2d8f3155ffa5019c394033d625254796c9a5e8..39fd8ced81da8b21e16b324098fddcc82bf689a5
--- a/device/esp32/tests_host/test_ble_provisioning_payload.cpp
+++ b/device/esp32/tests_host/test_ble_provisioning_payload.cpp
@@ -368,6 +368,40 @@
              "already_committed") == 0);
 }
 
+void test_duplicate_valid_write_gate() {
+  bool accepting_writes = true;
+  bool has_pending_result = true;
+  const bool valid_result = true;
+
+  assert(plantlab::provisioningShouldStopAcceptingWritesOnTake(
+      has_pending_result,
+      valid_result,
+      accepting_writes));
+
+  accepting_writes = false;
+  has_pending_result = false;
+  assert(plantlab::provisioningWriteRejectionError(
+             plantlab::ProvisioningState::PROVISIONING_BLE,
+             has_pending_result,
+             accepting_writes) == plantlab::ProvisioningParseError::kBusy);
+  assert(plantlab::provisioningWriteRejectionError(
+             plantlab::ProvisioningState::PROVISIONING_SUCCESS,
+             has_pending_result,
+             accepting_writes) == plantlab::ProvisioningParseError::kAlreadyCommitted);
+}
+
+void test_invalid_write_keeps_gate_open() {
+  assert(!plantlab::provisioningShouldStopAcceptingWritesOnTake(true, false, true));
+  assert(plantlab::provisioningWriteRejectionError(
+             plantlab::ProvisioningState::PROVISIONING_BLE,
+             false,
+             true) == plantlab::ProvisioningParseError::kNone);
+  assert(plantlab::provisioningWriteRejectionError(
+             plantlab::ProvisioningState::PROVISIONING_BLE,
+             true,
+             true) == plantlab::ProvisioningParseError::kBusy);
+}
+
 }  // namespace
 
 int main() {
@@ -385,5 +419,7 @@
   test_secret_masking();
   test_state_helpers();
   test_error_codes();
+  test_duplicate_valid_write_gate();
+  test_invalid_write_keeps_gate_open();
   return 0;
 }

tokens used
91,695
```

