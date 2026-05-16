# System Hardware Update

Describe the task here.
Feature request: Update PlantLab system hardware model and firmware/backend/mobile contract.

Context:
Before working on OTA, observability, long-run QA, notifications, or multi-device support, the PlantLab hardware configuration has changed and the system contract must be updated.

Hardware changes:
1. Removed water pump.
2. Removed soil moisture sensor.
3. Added water temperature sensor.
   - Sensor: DS18B20 waterproof temperature probe
   - GPIO: GPIO5
   - Protocol: 1-Wire
   - Typical wiring: VCC, GND, DATA
   - DATA should use a 4.7k pull-up resistor to VCC if not already included by adapter board.
4. Added water level sensor.
   - Connected to GPIO8
   - Uses ESP32 touch sensing / capacitive sensing
5. Grow LED changed.
   - Old: USB LED
   - New: PCB LED
   - LED driver: AL8860QMP-13
   - Control pin: GPIO15

Goal:
Update firmware, backend contract, mobile UI, docs, tests, and validation checklist so the system matches the new hardware configuration.

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current firmware sensor/actuator model.
- Study backend readings schema/API.
- Study mobile dashboard sensor display.
- Study docs and test files.
- Do not implement yet.
- Create a plan only.

Planner should investigate:

1. Firmware hardware mapping
- Remove old pump control path if no longer needed.
- Remove old soil moisture reading path if no longer needed.
- Add DS18B20 water temperature reading on GPIO5.
- Add water level touch sensor reading on GPIO8.
- Update PCB LED control on GPIO15.
- Confirm GPIO conflicts with existing BLE/Wi-Fi/I2C/button/status LED usage.
- Confirm touch sensor behavior on ESP32-S3 GPIO8.
- Confirm DS18B20 library/support in current firmware stack.
- Confirm LED driver control method: digital enable, PWM dimming, or both.

2. Backend data contract
- Replace or deprecate old fields:
  - soil_moisture
  - pump state/commands
- Add new fields:
  - water_temperature_c
  - water_level_raw or water_level_state
  - led_state or led_brightness if needed
- Decide migration/backward compatibility strategy.
- Avoid breaking existing deployed devices unless intentionally deprecated.
- Keep API versioning/backward-compatible behavior if practical.

3. Mobile dashboard
- Remove or hide soil moisture UI.
- Remove pump-related UI/commands.
- Add water temperature display.
- Add water level display.
- Update sensor trend cards.
- Update empty/error states.
- Update device status summary.
- Keep UI clean and premium.

4. Device commands
- Remove or disable pump commands.
- Keep/add LED commands appropriate for PCB LED.
- Decide whether LED supports:
  - on/off only
  - PWM brightness
  - schedule later
- Ensure backend command lifecycle still works.

5. Calibration and validation
- DS18B20 sanity range.
- Water temperature reading invalid/disconnected behavior.
- Water level capacitive baseline/calibration.
- Touch threshold strategy.
- LED on/off/PWM validation.
- Hardware manual test checklist.

6. Documentation
Update docs for:
- pin mapping
- sensor wiring
- backend fields
- mobile dashboard fields
- hardware validation checklist
- known removed hardware

7. Testing
Tester should verify:
- firmware compiles
- DS18B20 reading logic is testable where possible
- water level parser/state logic is testable where possible
- backend accepts new reading payload
- backend remains tolerant of old payload if required
- mobile renders new fields
- pump/moisture UI no longer appears in the new hardware profile
- no unrelated auth/provisioning behavior changes

8. Release Agent
Release Agent should check:
- firmware/backend/mobile contract alignment
- migration risk
- backward compatibility risk
- GCP deployment env impact
- manual hardware validation steps
- rollback notes

Important constraints:
- Board: ESP32-S3 master node.
- GPIO5 = DS18B20 water temperature data.
- GPIO8 = water level touch sensor.
- GPIO15 = PCB grow LED control through AL8860QMP-13.
- GPIO2 remains status LED unless current repo says otherwise.
- GPIO14 remains provisioning/reset button unless current repo says otherwise.
- Do not redesign BLE provisioning unless required by pin conflicts.
- Do not redesign backend auth.
- Do not add OTA yet.
- Do not add notifications yet.

Planner output format:
1. Current hardware/software contract summary
2. Hardware changes summary
3. GPIO conflict analysis
4. Firmware update plan
5. Backend API/schema update plan
6. Mobile UI update plan
7. Device command update plan
8. Calibration strategy
9. Backward compatibility/migration strategy
10. Files likely to change
11. Implementation phases
12. Test plan
13. Manual hardware validation checklist
14. Release/deployment considerations
15. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.