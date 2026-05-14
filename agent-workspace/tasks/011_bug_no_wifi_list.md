Feature request: Fix BLE provisioning Wi-Fi network list discovery.

Problem:
During BLE provisioning, the user should be able to choose their home Wi-Fi from a scanned list.
Currently, the Wi-Fi list is often empty or not shown, so the user must manually type the SSID.

Goal:
Make Wi-Fi SSID discovery reliable during BLE onboarding.

Use the existing multi-agent workflow:
Planner → wait for approval → Coder → Tester → Reviewer

Planner only:
- Study the current BLE provisioning flow.
- Study the current Wi-Fi scan implementation.
- Study the frontend/mobile provisioning UI that shows Wi-Fi networks.
- Do not implement yet.
- Create a plan only.

Areas to investigate:
1. ESP32 firmware Wi-Fi scan behavior
- Is Wi-Fi scan triggered during BLE provisioning?
- Is scan async or blocking?
- Is scan result stored correctly?
- Is scan allowed while BLE is active?
- Is Wi-Fi mode set correctly, for example WIFI_STA or WIFI_AP_STA?
- Is the scan happening before BLE client requests the list?
- Are scan results cleared too early?
- Are hidden networks filtered?
- Are duplicate SSIDs handled?
- Are 2.4 GHz vs 5 GHz networks handled correctly? ESP32 only sees 2.4 GHz Wi-Fi.

2. BLE transport/protocol
- Is there a BLE characteristic/command for requesting Wi-Fi scan?
- Is there a response path for scan results?
- Is response payload too large for BLE MTU?
- Are results chunked/paginated if needed?
- Are notify/indicate permissions correct?
- Does the app wait for scan completion before rendering?
- Are errors/timeouts surfaced clearly?

3. Frontend/mobile UI
- Does the UI actually request a scan?
- Does the UI subscribe to BLE notifications before requesting scan?
- Does it handle loading, empty state, retry, and manual SSID fallback?
- Does it parse the scan response correctly?
- Does it accidentally hide results because of filtering or state reset?

4. User experience
- Show loading state: “Scanning nearby Wi-Fi…”
- Show retry button if no networks are found.
- Keep manual SSID input as fallback.
- Explain that ESP32 only supports 2.4 GHz Wi-Fi.
- Deduplicate SSIDs and sort by signal strength if RSSI is available.

5. Reliability requirements
- Wi-Fi scan should not break BLE provisioning session.
- BLE connection should remain stable during scan.
- Scan timeout should be handled.
- Large scan results should not overflow BLE payload.
- No Wi-Fi password or device token should be logged.
- Existing BLE credential submit flow must keep working.

Expected design:
Planner should propose one of these approaches:
A. Phone/app scans Wi-Fi networks and sends selected SSID to device.
B. ESP32 scans Wi-Fi and sends SSID list over BLE.
C. Hybrid approach with manual fallback.

Planner should compare the tradeoffs and recommend the best approach for this repo.

Tester Agent should verify:
- scan request command works
- scan success with multiple networks
- scan empty result
- scan timeout
- duplicate SSIDs
- hidden SSIDs
- large result list / BLE chunking
- manual SSID fallback still works
- credential submission still works after scan
- no secrets in logs

Reviewer Agent should block if:
- BLE payload can overflow
- UI can get stuck in loading state
- manual SSID fallback is removed
- ESP32 5 GHz limitation is not explained to user
- BLE provisioning becomes less reliable
- secrets are logged
- implementation changes unrelated auth/backend behavior

Planner output format:
1. Current flow summary
2. Root cause hypotheses
3. Recommended approach
4. BLE protocol changes if needed
5. Firmware changes
6. Frontend/mobile changes
7. UX behavior
8. Files likely to change
9. Implementation steps
10. Test plan
11. Manual hardware validation checklist
12. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.