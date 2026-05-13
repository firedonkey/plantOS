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