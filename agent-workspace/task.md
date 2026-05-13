Feature request: Add BLE provisioning for PlantLab ESP32 master node.

Goal:
Allow a user to put the ESP32 master node into BLE provisioning mode, send Wi-Fi credentials and the PlantLab device token over BLE, save them, then reboot/connect to Wi-Fi and resume normal backend communication. This BLE provisioning will replace the current provisioing by softAP on ESP32. you can try to reuse the procesure of current provisioining, but instead of using softAP, we swtich to BLE. The goal is to make user experience easier. 

Use the existing 4-agent workflow:
Planner → wait for my approval → Coder → Tester → Reviewer.

Planner Agent instructions:
- Study the current firmware repo before designing.
- Do not write production code.
- Create agent-workspace/plan.md only.
- Include BLE architecture, provisioning state machine, security design, storage design, API/backend impact, test plan, and risks.

Hardware constraints:
- Board: ESP32-S3-DevKitC-1-N32R16V.
- Status LED: GPIO2.
- Provisioning button: GPIO14.
- Existing firmware already has Wi-Fi/device-token flow.
- Existing backend already uses device tokens.
- BLE provisioning should be additive.
- Do not remove SoftAP provisioning if it already exists.

Expected user flow:
1. User long-presses GPIO14.
2. Device enters BLE provisioning mode.
3. Status LED indicates provisioning mode.
4. Phone/computer connects over BLE.
5. Client sends:
   - Wi-Fi SSID
   - Wi-Fi password
   - PlantLab device token
6. ESP32 validates payload format.
7. ESP32 saves credentials securely.
8. ESP32 exits provisioning mode and connects to Wi-Fi.
9. ESP32 resumes normal backend heartbeat/registration using the device token.

Security requirements:
- Never log Wi-Fi password.
- Never log full device token.
- Mask token in logs.
- Prefer secure/non-volatile storage supported by ESP32 platform.
- Handle invalid payload safely.
- Handle BLE timeout.
- Handle disconnect during provisioning.
- Do not break existing device-token behavior.

Implementation requirements after approval:
- Keep changes small and easy to review.
- Add clear state names, for example:
  - NORMAL
  - PROVISIONING_BLE
  - WIFI_CONNECTING
  - PROVISIONING_FAILED
  - PROVISIONING_SUCCESS
- Add tests or mocks where possible.
- If real BLE hardware testing is not possible, create unit-testable parsing/state logic.
- Update documentation with how to use BLE provisioning.

Tester Agent should verify:
- Valid provisioning payload.
- Missing SSID.
- Missing password.
- Missing token.
- Invalid JSON or malformed payload.
- Timeout.
- Secret masking in logs.
- Existing Wi-Fi flow still works.
- Existing backend heartbeat still works.

Reviewer Agent should block if:
- Secrets are logged.
- Existing provisioning is broken.
- Device token behavior changes unexpectedly.
- BLE code is too tightly coupled to core logic.
- No testable provisioning state/parser logic exists.
- Plan was not followed.

Final output should include:
- Changed files
- How to enter BLE provisioning mode
- How to send BLE credentials
- Test result summary
- Known limitations