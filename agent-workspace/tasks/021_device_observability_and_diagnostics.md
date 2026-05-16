Feature request: Device observability and diagnostics for PlantLab.

Context:
PlantLab now has real provisioning, camera upload, GCP deployment, and updated hardware sensors.

Goal:
Improve visibility into device health, firmware behavior, connectivity, and failures.

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current heartbeat/status APIs.
- Study master firmware logs/status reporting.
- Study camera firmware logs/status reporting.
- Study mobile device status UI.
- Do not implement yet.
- Create a plan only.

Core diagnostics to support:
1. Device online/offline status.
2. Last heartbeat timestamp.
3. Firmware version.
4. Uptime.
5. Wi-Fi RSSI.
6. Reboot reason if available.
7. Provisioning state.
8. Last sensor reading time.
9. Last camera image upload time.
10. Last command result.
11. OTA status if task 020 is complete or planned.
12. Error counters:
    - Wi-Fi reconnects
    - upload failures
    - BLE provisioning failures
    - ESP-NOW failures if camera nodes use ESP-NOW

Backend requirements:
- Store latest diagnostic snapshot per device.
- Keep recent diagnostic events if practical.
- Avoid storing excessive logs.
- Provide API for mobile/web device health view.

Firmware requirements:
- Report compact diagnostics in heartbeat.
- Avoid sending huge logs.
- Avoid sending secrets.
- Include useful failure codes.

Mobile requirements:
- Add device health/status view.
- Show friendly status:
  - Online
  - Recently seen
  - Offline
  - Needs attention
- Show technical diagnostics in a dev/support section.

Security/privacy:
- Never send Wi-Fi password.
- Never send full tokens.
- Mask sensitive identifiers where needed.
- Avoid logging secrets.

Tester should verify:
- backend accepts diagnostic payload
- mobile renders missing/partial diagnostics safely
- firmware builds
- offline state is handled
- diagnostic payload is backward compatible if possible

Reviewer should block if:
- secrets are logged
- diagnostic payload is too large/noisy
- mobile crashes on missing fields
- backend schema becomes hard to maintain
- unrelated auth/provisioning behavior changes

Release Agent should verify:
- migration risk
- production storage impact
- observability value
- rollout checklist
- rollback notes

Planner output format:
1. Current observability summary
2. Diagnostic data model recommendation
3. Firmware heartbeat update plan
4. Backend API/schema plan
5. Mobile diagnostics UI plan
6. Event/log retention strategy
7. Security rules
8. Files likely to change
9. Implementation phases
10. Test plan
11. Manual hardware validation checklist
12. Release/deployment considerations
13. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.