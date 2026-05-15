Feature request: Factory reset and re-provisioning UX for PlantLab devices.

Context:
BLE provisioning is working.
Mobile app onboarding exists.
Camera and backend connectivity are working.

Goal:
Create a safe, understandable, and recoverable factory reset + re-provisioning experience for PlantLab devices.

The user should be able to:
- reset a device safely
- reconnect the device to a new Wi-Fi network
- move the device to another account/home
- recover from provisioning failures
- understand what state the device is in

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current provisioning architecture.
- Study firmware provisioning state handling.
- Study backend device/account linking behavior.
- Study mobile onboarding flow.
- Do not implement yet.
- Create a plan only.

Core scenarios to support:

1. Wi-Fi changed
User gets a new router or changes Wi-Fi password.

Desired UX:
- user enters reset/re-provisioning mode
- device advertises over BLE again
- user reconnects device using app
- existing account ownership remains intact if appropriate

2. Device transferred to another user
Desired UX:
- previous ownership removed safely
- device can be claimed again
- avoid accidental hijacking

3. Provisioning failed halfway
Desired UX:
- device can recover cleanly
- no confusing broken state
- user can retry onboarding easily

4. User wants full factory reset
Desired UX:
- clear warning
- wipe local provisioning data safely
- wipe device token safely
- return to onboarding mode

Planner should investigate:

1. Firmware reset architecture
- where provisioning state is stored
- how Wi-Fi credentials are stored
- how device token is stored
- how to safely erase/reset
- how BLE provisioning mode is re-entered
- whether reboot is required

2. Button behavior
Current hardware:
- GPIO14 provisioning/reset button
- GPIO2 status LED

Planner should define:
- short press behavior
- long press behavior
- reset hold duration
- accidental reset prevention
- LED state meanings

3. Mobile UX
- where reset/re-provisioning starts
- warning/confirmation flow
- reconnect guidance
- onboarding recovery messaging
- device state visibility

4. Backend/device ownership
Planner should decide:
- whether factory reset unlinks backend ownership immediately
- whether backend retains historical data
- whether “unclaimed device” state exists
- whether device token rotates after reset
- how to prevent duplicate device records

5. Device identity
- preserve hardware identity?
- rotate credentials?
- preserve serial/device id?
- claim-token flow implications

6. Failure handling
- interrupted reset
- power loss during reset
- Wi-Fi reconnect failure
- BLE reconnect failure
- partially erased state

7. Security
- prevent unauthorized reset if possible
- avoid exposing secrets
- wipe tokens securely
- prevent accidental account hijacking

Desired UX direction:
- simple
- calm
- understandable
- minimal user confusion
- Apple/HomeKit-like onboarding recovery feel

Potential user flow:
1. User opens device settings.
2. User selects:
   - reconnect Wi-Fi
   - re-provision device
   - factory reset
3. App guides user:
   - hold button for X seconds
   - device enters BLE mode
   - reconnect flow starts
4. Device reconnects or resets safely.
5. App confirms success.

Tester should verify:
- reset clears provisioning correctly
- device re-enters BLE provisioning mode
- reconnect flow works
- existing device record behavior is correct
- no duplicate/broken backend state
- interrupted reset recovery works
- accidental short press does not wipe device
- secrets/tokens are not exposed in logs

Reviewer should block if:
- reset can accidentally brick onboarding
- duplicate backend device records become common
- ownership transfer is unsafe
- tokens are not rotated/wiped appropriately
- BLE reprovisioning becomes less reliable
- unrelated auth/backend behavior changes unnecessarily

Release Agent should verify:
- firmware/backend/mobile compatibility
- migration impact
- user support implications
- rollback/recovery notes
- release checklist

Planner output format:
1. Current provisioning/reset behavior summary
2. Main UX/reliability problems
3. Recommended reset architecture
4. Firmware reset flow
5. Mobile UX flow
6. Backend ownership strategy
7. Security considerations
8. Button/LED behavior
9. Failure recovery behavior
10. Files likely to change
11. Implementation phases
12. Test plan
13. Manual hardware validation checklist
14. Risks and assumptions
