# PlantLab Real Device Onboarding Validation Plan

## Purpose

Use this plan to validate PlantLab onboarding with real hardware before GCP
deployment and long-duration reliability testing. This plan covers real iPhone,
real BLE, real Wi-Fi, the ESP32 master node, and the ESP32 camera node.

This is a validation plan only. Do not redesign onboarding, change firmware,
change backend APIs, change BLE payloads, or change claim-token behavior while
executing these tests. Record issues first, then decide fixes separately.

## Test Environment

Required:

- iPhone with the current local PlantLab mobile development build installed.
- ESP32-S3 master node with the target firmware build.
- ESP32-S3 camera node with the target firmware build.
- Local backend running and reachable from the iPhone.
- Provisioning backend running and reachable from the iPhone.
- 2.4 GHz Wi-Fi network with known password.
- Optional weak-signal location at least one room away from the router.
- Access to backend, firmware, and mobile logs.

Recommended local services:

```sh
cd /Users/gary/plantOS
docker compose -f platform/infra/docker/docker-compose.local.yml up --build
```

Recommended mobile local build target:

```sh
cd /Users/gary/plantOS
npm --prefix platform/mobile run start:dev:local -- --api-url http://YOUR_LAPTOP_LAN_IP:8000
```

Use the laptop LAN IP that the iPhone can reach. Do not use `localhost` from the
iPhone.

## Device Requirements

Before each test run, record:

- Master firmware version.
- Camera firmware version.
- Master serial port, if connected.
- Camera serial port, if connected.
- Device hardware ID if visible in logs or dashboard.
- Account used for the test.
- Whether the device starts as unclaimed, already claimed, released, or reset.

Button behavior expected by the current firmware:

- Hold setup button for 5 seconds: enter setup or Wi-Fi recovery mode.
- Hold setup button for 20 seconds: full local factory reset.
- Slow blink: setup/provisioning mode.
- Fast blink: factory reset accepted or pending.

## Wi-Fi Requirements

Use at least these networks or simulated conditions:

- Good 2.4 GHz Wi-Fi near the device.
- Wrong password for the same Wi-Fi.
- Temporarily unavailable Wi-Fi, for example router off or SSID hidden.
- Weak Wi-Fi location where RSSI is expected to be low.

Record Wi-Fi SSID, approximate device location, and whether the phone and
backend are on the same reachable network.

## Standard Test Record

For every scenario, record:

- Test ID:
- Date/time:
- Tester:
- App version/build:
- Master firmware version:
- Camera firmware version:
- Account:
- Starting ownership state:
- Scenario:
- Onboarding start time:
- Onboarding completion time:
- Total duration:
- Number of taps:
- Number of retries:
- Error messages shown:
- User confusion points:
- Recovery action used:
- Recovery succeeded: yes/no
- Device appeared online: yes/no
- First heartbeat received: yes/no
- First sensor reading received: yes/no
- First image received: yes/no
- Camera node status:
- Backend logs collected: yes/no
- Firmware logs collected: yes/no
- Mobile logs/screenshots collected: yes/no
- Result: pass/fail/blocked
- Issue IDs created:
- Notes:

## Validation Matrix

| Scenario | Expected Result | Pass Criteria |
| --- | --- | --- |
| 1. Happy path onboarding | User finds PlantLab, sends Wi-Fi, setup completes, dashboard opens. | Completes under 90 seconds, no app restart, device appears online, first heartbeat received, no unclear messaging. |
| 2. Wrong Wi-Fi password | App reports Wi-Fi could not connect and returns user to recovery path. | Error says to check password, user can change Wi-Fi details, no dead-end spinner. |
| 3. Weak Wi-Fi signal | Setup either completes slowly or shows useful recovery guidance. | User sees progress or a clear retry action; device does not get stuck in an unclear state. |
| 4. Wi-Fi unavailable | PlantLab cannot join Wi-Fi and app explains the network issue. | User can retry or change Wi-Fi; existing device config is not lost during Wi-Fi recovery if applicable. |
| 5. BLE disconnect during setup | App explains the PlantLab connection was interrupted. | User can reconnect or restart setup without technical BLE wording. |
| 6. App backgrounded during setup | App resumes with a useful setup state or recovery path. | No crash; user can keep waiting, retry check, or restart setup. |
| 7. Device reboot during setup | App waits through reboot and continues checking online status. | User sees setup progress; no misleading success before backend check-in. |
| 8. Factory reset and setup again | Device clears local config, restarts, then can be added again. | Reset instructions match 20-second behavior; post-reset waiting guidance is clear; setup succeeds afterward. |
| 9. Ownership conflict | Account B tries to add device owned by Account A. | App shows already-connected message, explains previous owner or reset path, and avoids claim-token/backend wording. |
| 10. Change Wi-Fi | Existing account changes network through recovery flow. | 5-second setup instruction is clear; device remains in same account and history remains visible. |
| 11. Reconnect PlantLab | Offline device is repaired through reconnect flow. | App verifies correct hardware and gives a useful path back to dashboard. |
| 12. Slow registration | Device joins Wi-Fi but backend registration/check-in is slow. | Waiting state remains understandable; after timeout user has clear next actions. |
| 13. Delayed heartbeat | Device is registered but first heartbeat is delayed. | App does not require image readiness; user sees setup or dashboard state that explains waiting. |
| 14. Delayed ownership release | Account A releases, Account B tries before device reset/retry is complete. | App tells user to wait/retry or reset; no dead-end or contradictory ownership message. |
| 15. Camera node not ready | Master completes onboarding before camera is fully ready. | Onboarding does not block on camera; dashboard can show camera waiting later. |
| 16. Multiple setup attempts | User retries setup repeatedly after failures. | No duplicate confusing devices; app retains a consistent recovery path. |

## Pass / Fail Criteria

### Happy Path Pass Criteria

Happy path passes only if:

- Setup completes in 90 seconds or less from tapping Find PlantLab.
- No app restart is required.
- No unclear or technical error appears.
- Device appears online in the dashboard.
- First heartbeat is visible in backend/device state.
- User can understand the current setup step at all times.

Recommended secondary targets:

- First sensor reading arrives within the normal sensor loop timing.
- First image arrives if the camera node is ready, but onboarding must not block
  only because the camera is delayed.

### Recovery Pass Criteria

Recovery scenarios pass only if:

- The user always has a visible next action.
- There are no dead-end screens.
- Retry path is available.
- Change Wi-Fi path is available where relevant.
- Reset guidance is available where relevant.
- Error copy avoids BLE, claim-token, backend, or protocol terminology.
- Recovery succeeds or produces an actionable issue with logs.

### Failure Criteria

Mark a scenario failed if any of these occur:

- App crashes or requires force quit.
- User sees only a spinner after the timeout.
- User cannot retry or change Wi-Fi after failure.
- Ownership conflict message does not explain what to do.
- Device appears in the wrong account.
- Device gets stuck requiring database edits.
- Firmware reset guidance does not match real LED/button behavior.
- Onboarding blocks only because the camera node is delayed.

## Logging Checklist

Collect only the logs needed to diagnose the issue.

Backend:

- Provisioning backend logs around setup-token creation and registration.
- Platform backend logs around setup status polling.
- Device timeline events.
- Diagnostics timeline events.
- Any 4xx/5xx responses during onboarding.

Firmware:

- Master provisioning state logs.
- Master Wi-Fi connect logs.
- Master registration logs.
- Master factory reset logs.
- Camera provisioning and health logs.
- Camera image upload logs if camera readiness is part of the scenario.

Mobile:

- Screenshot or screen recording of the onboarding flow.
- Visible error message text.
- Approximate stage where the issue occurred.
- App build version and API URL.

Useful terminal commands:

```sh
docker logs -f plantlab-local-platform
docker logs -f plantlab-local-provision-backend
.venv/bin/pio device monitor -d device/esp32 -e esp32-local --port /dev/cu.usbmodem1301
```

Adjust the serial port for the connected board.

## Factory Reset Validation Checklist

Use this when validating reset, reused development units, and Account B setup.

1. Confirm device is currently connected to Account A.
2. Confirm Account A dashboard shows the device before reset.
3. Hold setup button for 20 seconds.
4. Verify fast blink appears.
5. Wait for restart.
6. Confirm app displays post-reset waiting guidance if using reset instructions.
7. Log in as Account B.
8. Start Add Device.
9. Hold setup button for 5 seconds if needed to enter setup mode.
10. Complete Wi-Fi setup.
11. Confirm device appears in Account B.
12. Confirm Account B sees online state after heartbeat.
13. Confirm Account A no longer actively controls this hardware if ownership transfer was expected.

Pass if the user can complete these steps without database edits or engineering
support.

## Ownership Validation Checklist

Run these ownership cases:

- Device owned by Account A, Account B attempts setup without reset.
- Account A taps prepare for transfer, then device is reset and Account B sets up.
- Device is factory reset offline, then Account B provisions it.
- Account B retries too soon after reset.
- Account A removes/releases device but physical device is not reset.

Expected behavior:

- Account B sees a clear already-connected message when appropriate.
- App explains previous owner removal or full reset without backend terminology.
- Account B can proceed after legitimate full reset.
- No scenario silently assigns the hardware to the wrong account.

## Camera Node Validation Checklist

Run these cases:

- Camera node powered before master setup.
- Camera node powered after master setup.
- Camera node temporarily offline during setup.
- Camera image upload delayed.

Expected behavior:

- Master onboarding completes without requiring the camera node.
- Dashboard can show camera waiting or offline after setup.
- First image appears after camera readiness and capture/upload.
- No onboarding error says setup failed only because camera image is delayed.

## Test Execution Guide

For each scenario:

1. Pick the scenario from the validation matrix.
2. Reset or prepare the device to the required starting state.
3. Start screen recording on the iPhone if possible.
4. Start firmware serial log capture if the device is connected.
5. Start backend log capture.
6. Open the mobile app and confirm the API target is correct.
7. Execute the scenario exactly once.
8. Record timing, taps, retries, messages, and outcome.
9. If it fails, create an issue using `docs/testing/onboarding_issue_template.md`.
10. Attach screenshots and relevant log excerpts.
11. Restore the device to a known state before the next scenario.

## Recommended First Test Order

1. Happy path
2. Wrong password
3. Factory reset
4. Ownership conflict
5. BLE disconnect
6. Weak Wi-Fi
7. App backgrounding
8. Device reboot during setup

This order establishes the baseline first, then tests the most likely real-world
recovery paths.

## Stop Conditions

Stop validation and file an issue if:

- The app cannot find a known-good device in setup mode.
- Happy path cannot complete after two clean attempts.
- Device binds to the wrong account.
- Factory reset instructions do not match hardware behavior.
- Backend or firmware logs show repeated crashes.
- A scenario would require changing firmware, backend API, BLE protocol, or
  claim-token architecture during the test.

## Remaining Risks

- Real BLE behavior must be validated on an installed iOS development build, not
  only simulator or Expo preview.
- Network isolation between phone and laptop can look like provisioning failure.
- Camera readiness can lag master readiness and should be treated as a separate
  dashboard readiness check.
- Ownership transfer behavior depends on correct backend state and full local
  reset behavior.
