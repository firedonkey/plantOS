Feature request: Hardware validation and long-run QA for PlantLab.

Context:
Core PlantLab features are working. Hardware has changed:
- removed pump
- removed soil moisture sensor
- added DS18B20 water temperature sensor on GPIO5
- added water level touch sensor on GPIO8
- PCB LED controlled by GPIO15 through AL8860QMP-13

Goal:
Create a structured validation and long-run QA system for real hardware.

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current firmware.
- Study backend telemetry.
- Study mobile dashboard.
- Study existing test/checklist docs.
- Do not implement yet.
- Create a plan only.

Validation targets:
1. Boot stability.
2. BLE provisioning.
3. Wi-Fi reconnect.
4. Backend heartbeat.
5. DS18B20 water temperature reading.
6. Water level touch sensor reading.
7. PCB LED control.
8. Camera heartbeat.
9. Camera image capture/upload.
10. Mobile dashboard refresh.
11. GCP backend stability.
12. Recovery after power loss.
13. Recovery after router reboot.
14. Overnight soak test.

Expected deliverables:
- hardware validation checklist
- 2-hour soak test checklist
- overnight soak test checklist
- failure logging template
- backend/mobile/firmware improvements if needed
- optional scripts for collecting logs

Planner should define:
- test steps
- expected results
- pass/fail criteria
- metrics to capture
- hardware setup
- failure categories
- recovery behavior

Tester should verify:
- firmware compile
- backend tests pass
- mobile typecheck passes
- checklist docs are complete
- any log collection scripts are safe

Reviewer should block if:
- checklist is vague
- hardware validation misses new sensors
- long-run QA has no pass/fail criteria
- scripts expose secrets
- unrelated product behavior changes

Release Agent should verify:
- readiness for real-world testing
- manual validation steps
- known risks
- rollback/recovery notes

Planner output format:
1. Current hardware QA readiness summary
2. Hardware validation checklist
3. Sensor validation plan
4. LED validation plan
5. Camera validation plan
6. Connectivity/recovery validation plan
7. 2-hour soak test plan
8. Overnight soak test plan
9. Metrics/logs to collect
10. Failure report template
11. Files likely to change
12. Implementation phases
13. Test plan
14. Release/deployment considerations
15. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.