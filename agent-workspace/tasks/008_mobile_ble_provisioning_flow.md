Feature request: Implement in-app BLE provisioning flow for mobile development build.

Problem:
Now that the PlantLab mobile app has a native iOS development build, provisioning should be done inside the PlantLab app instead of manually using nRF Connect.

Goal:
Allow the mobile app to send provisioning information to the ESP32 over BLE:
- Wi-Fi SSID
- Wi-Fi password
- PlantLab device token

This should replace the manual nRF Connect step for normal development testing.

Use existing multi-agent workflow:
Planner → approval → Coder → Tester → Reviewer

Planner only:
- Study current mobile app structure.
- Study current ESP32 BLE provisioning service/characteristic UUIDs.
- Study current provisioning payload format.
- Study existing BLE library/config.
- Do not implement yet.
- Create a plan only.

Important:
- This task is for the native development build, not Expo Go.
- Expo Go compatibility is not required.
- Do not redesign firmware protocol unless necessary.
- Do not change backend auth unless necessary.
- Manual nRF Connect can remain as a debugging fallback, but should not be the primary workflow.

Planner should investigate:
1. Current BLE provisioning protocol
- service UUID
- write characteristic UUID
- notify/read characteristic UUID if present
- payload format
- expected ACK/status response
- MTU/chunking requirement
- timeout behavior

2. Mobile app BLE implementation
- current BLE package
- whether react-native-ble-plx is already installed
- app config/plugin permissions
- iOS Bluetooth permission text
- connection lifecycle
- scan/connect/disconnect behavior

3. In-app provisioning UX
- screen or flow for provisioning
- device scan
- connect to PlantLab device
- choose or enter Wi-Fi SSID
- enter Wi-Fi password
- select/provide device token
- send provisioning payload
- show progress/status
- show success/failure
- retry support

4. Security
- never log Wi-Fi password
- never log full device token
- mask token in UI/logs
- do not persist Wi-Fi password in app unless necessary
- use secure storage only if needed

5. Testing
- unit-test payload builder
- mock BLE client if possible
- test success/error states
- test missing SSID/password/token
- test disconnected device
- test write failure
- test timeout
- test ACK/status parsing

Recommended implementation direction:
- Add a BLE provisioning service module in the mobile app.
- Add a payload builder/parser that is unit-testable without hardware.
- Add UI state machine for provisioning.
- Use BLE write with response for provisioning payload.
- Subscribe to notify/read status if firmware supports it.
- Keep manual SSID fallback.
- Keep nRF Connect instructions only as debug fallback docs.

Reviewer should block if:
- Wi-Fi password or full token is logged.
- BLE write uses wrong encoding.
- Payload builder is not testable.
- App can get stuck in loading state.
- Manual fallback is removed.
- Expo Go assumptions remain.
- Native iOS permission setup is missing.
- Firmware/backend behavior is changed unnecessarily.

Planner output format:
1. Current mobile app BLE readiness summary
2. Current firmware BLE protocol summary
3. Recommended in-app provisioning architecture
4. BLE service/characteristic usage
5. Payload format and encoding
6. UI/UX flow
7. Security rules
8. Files likely to change
9. Implementation steps
10. Test plan
11. Manual hardware validation checklist
12. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.