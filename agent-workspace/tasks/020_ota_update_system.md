Feature request: OTA firmware update system for PlantLab devices.

Context:
PlantLab hardware contract has been updated. BLE provisioning, camera, backend, mobile app, and GCP deployment are working.

Goal:
Design and implement a safe OTA firmware update system for PlantLab master and camera nodes.

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current ESP32 master firmware.
- Study camera-node firmware.
- Study backend device model.
- Study firmware version reporting if any.
- Do not implement yet.
- Create a plan only.

Core requirements:
1. Device reports firmware version to backend.
2. Backend can know current firmware version per device.
3. Backend can advertise available firmware update.
4. Device can download firmware update safely.
5. Device validates update before applying.
6. Device reports OTA status.
7. Failed OTA should not brick device.
8. OTA should support master node first; camera node can be planned as phase 2 if needed.

Planner should investigate:
- ESP32 OTA support in current firmware stack.
- Flash partition requirements.
- Firmware artifact hosting strategy.
- Firmware version format.
- Update manifest format.
- Rollback behavior.
- Power-loss failure handling.
- Backend API needs.
- Mobile UI needs for update visibility.

Security requirements:
- Firmware URLs should not expose secrets.
- OTA should verify firmware integrity.
- Use checksum at minimum.
- Consider signed firmware if practical.
- Do not allow arbitrary firmware URL injection.

Backend requirements:
- Store device firmware version.
- Store update availability.
- Store update status:
  - idle
  - available
  - downloading
  - installing
  - success
  - failed
- Add command or API contract for OTA update.

Mobile requirements:
- Show firmware version.
- Show update status.
- Show update available if backend supports it.
- Do not make mobile responsible for firmware upload in this task.

Tester should verify:
- firmware compile
- version reporting
- manifest parsing
- checksum validation if implemented
- failed download behavior
- backend OTA status APIs
- mobile display does not crash without OTA data

Reviewer should block if:
- OTA can brick device easily
- no validation/checksum exists
- backend can trigger arbitrary URL update unsafely
- firmware/backend contract is unclear
- unrelated provisioning/auth behavior changes

Release Agent should verify:
- firmware/backend/mobile contract alignment
- deployment risk
- rollback notes
- manual hardware validation checklist
- production rollout recommendation

Planner output format:
1. Current firmware update readiness summary
2. Recommended OTA architecture
3. Firmware update flow
4. Backend API/data model plan
5. Firmware artifact hosting plan
6. Security/integrity plan
7. Mobile UI plan
8. Rollback/failure recovery plan
9. Files likely to change
10. Implementation phases
11. Test plan
12. Manual hardware validation checklist
13. Release/deployment considerations
14. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.