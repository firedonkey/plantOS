# Task: Make PlantLab BLE Provisioning Reliable and Smooth

## Context

PlantLab BLE provisioning is currently working, but it is fragile.

The goal is to improve reliability and user onboarding without breaking the current working BLE provisioning path.

This task should be handled by the multi-agent system in small, reviewable steps. Agents should inspect the current implementation before making changes.

## Core Rule

No agent may rewrite the provisioning architecture.

The current BLE provisioning flow is working. This task is about making it more reliable, more predictable, and smoother for users. Do not redesign the whole system.


---

## Main Goals

1. Make BLE provisioning more reliable.
2. Give provisioning higher priority than normal device tasks.
3. Improve the iOS onboarding flow.
4. Reduce unnecessary user input.
5. Add clear logs and acceptance checks.

---

## Product Behavior Requirements

### 1. Long Press Enters Provisioning Mode

Long press should be used only for provisioning.

When the user long-presses the device button:

- The device should immediately enter provisioning mode.
- Provisioning should have higher priority than normal tasks.
- BLE advertising / BLE provisioning should start as soon as possible.
- Normal background work should pause or defer while provisioning is active.

Lower-priority tasks to pause or defer:

- Scheduled camera capture
- Manual camera capture if not already critical
- Image upload retry loops
- Backend message sending
- Heartbeat
- Periodic sync jobs
- Any non-critical background task

Critical services that may remain active:

- Button handling
- BLE provisioning service
- Minimal logging
- Wi-Fi connection attempt after credentials are received
- Device-online confirmation after provisioning

---

## Important Technical Concern

ESP32 Wi-Fi and BLE can coexist, but they share radio resources.

This means BLE provisioning may become fragile if the device is also doing heavy Wi-Fi work, uploading, retrying, or sending messages.

The desired behavior is:

- Provisioning mode should temporarily reduce competing Wi-Fi/background activity.
- BLE should not be blocked by camera, upload, or backend retry tasks.
- After provisioning finishes, normal tasks should resume.

---

## ESP32 Firmware Requirements

### Provisioning State Machine

Add or improve a clear provisioning state machine.

Suggested states:

```text
NORMAL
PROVISIONING_REQUESTED
PROVISIONING_ACTIVE
BLE_CONNECTED
CREDENTIALS_RECEIVED
WIFI_CONNECTING
WIFI_CONNECTED
BACKEND_CONFIRMING
PROVISIONING_SUCCESS
PROVISIONING_FAILED
PROVISIONING_TIMEOUT
```

The exact state names can be adjusted to match the current codebase, but the behavior should remain clear.

### Provisioning Priority

When provisioning starts:

1. Set a global/system provisioning flag.
2. Pause or defer non-critical tasks.
3. Start BLE advertising.
4. Accept credentials over BLE.
5. Attempt Wi-Fi connection.
6. Confirm device is online with backend.
7. Exit provisioning mode after success, failure, timeout, or cancel.
8. Resume normal tasks.

### Timeout

Add a provisioning timeout.

Recommended default:

```text
3 to 5 minutes
```

If timeout occurs:

- Stop BLE provisioning.
- Resume normal tasks.
- Log the timeout clearly.
- Do not leave the device stuck in provisioning mode.

### Logging

Add clear logs for each major step:

```text
[provisioning] provisioning_requested
[provisioning] normal_tasks_paused
[provisioning] ble_advertising_started
[provisioning] ble_connected
[provisioning] credentials_received
[provisioning] wifi_connecting ssid=<ssid>
[provisioning] wifi_connected
[provisioning] backend_confirming
[provisioning] device_online_confirmed
[provisioning] provisioning_success
[provisioning] provisioning_failed reason=<reason>
[provisioning] provisioning_timeout
[provisioning] normal_tasks_resumed
```

Do not log Wi-Fi passwords or secrets.

---

## iOS App Requirements

### 1. Device Name

Use default device name:

```text
Smart Planter
```

The user should not need to type a device name during basic onboarding.

### 2. Remove Location Field

Remove the location field from onboarding.

Reason:

- Most users will not use it.
- It creates unnecessary friction.
- Location can be added later as an optional advanced setting if needed.

### 3. BLE Pairing Waiting State

When the iOS app is pairing or connecting to ESP32 over BLE:

- Show an animation or loading state.
- Do not leave the screen blank.
- Show friendly text.

Suggested text:

```text
Connecting to your Smart Planter...
```

### 4. Nearby Wi-Fi Scan Waiting State

When scanning nearby Wi-Fi networks:

- Show animation/loading state.
- Disable repeated scan taps while scan is active.
- Show error state if scan fails or times out.

Suggested text:

```text
Scanning nearby Wi-Fi networks...
```

### 5. Wi-Fi Password UX

Important iOS limitation:

The iOS app cannot read the iPhone's saved Wi-Fi password.

Do not try to implement automatic Wi-Fi password extraction.

Desired behavior:

- If the app can detect the iPhone's current SSID, preselect that SSID.
- Still ask the user to enter the Wi-Fi password.
- Use simple helper text.

Suggested text:

```text
Enter the Wi-Fi password for this network.
```

If the user selects a different SSID:

- Ask for that network's password normally.

Password handling:

- Do not permanently store the password unless a secure storage design already exists.
- Prefer keeping the password only in memory during provisioning.
- Never log the password.

### 6. Rename Button

Rename:

```text
Send provisioning over BLE
```

to:

```text
Confirm
```

### 7. Wait for Device Online

After provisioning info is sent over BLE:

- Show another waiting animation.
- Poll backend or device status.
- Wait for the device to come online.
- Once online, navigate automatically to the device dashboard page.

Suggested text:

```text
Connecting your Smart Planter...
This may take a moment.
```

---

## Backend / API Requirements

After the iOS app sends credentials over BLE:

- The app should check whether the device becomes online.
- Use existing backend heartbeat/device-status endpoint if available.
- If no endpoint exists, inspect current backend design and propose the smallest safe addition.

Suggested behavior:

```text
poll every 2 seconds
timeout after 60 to 90 seconds
```

Success:

- Device reports online.
- App navigates to device dashboard.

Failure / timeout:

- Show retry-friendly error.
- Do not trap the user in a loading screen.

Suggested error text:

```text
We could not confirm your Smart Planter is online yet.
Please make sure your Wi-Fi password is correct and the device is nearby.
```


## Implementation Phases

### Phase A: Inspect and Plan

Before changing code, each agent should inspect the current codebase and report:

- Relevant files
- Current flow
- Current risks
- Minimal proposed changes

No large refactor should happen in this phase.

### Phase B: Firmware Reliability

Implement provisioning priority behavior:

- Long press enters provisioning mode.
- Pause/defer background tasks.
- Start BLE reliably.
- Add timeout.
- Add logs.
- Resume normal tasks.

### Phase C: iOS Onboarding UX

Implement smoother onboarding:

- Default name
- Remove location
- Loading animations
- Better button text
- Password UX
- Wait-for-online screen
- Dashboard redirect

### Phase D: Backend Online Detection

Use or add minimal backend support for:

- Device online status
- Polling from iOS
- Timeout handling

### Phase E: QA and Regression

Run through complete test cases.

---

## Acceptance Criteria

### Firmware Acceptance Criteria

- Long press always enters provisioning mode.
- Provisioning mode starts even if Wi-Fi/backend/camera task is busy.
- BLE provisioning does not get blocked by scheduled capture or upload retries.
- Device does not get stuck in provisioning mode.
- Normal tasks resume after provisioning exits.
- Timeout works.
- Logs clearly show provisioning progress.
- No password or secret is logged.

### iOS Acceptance Criteria

- Default device name is `Smart Planter`.
- Location field is removed.
- BLE pairing has visible loading animation/state.
- Wi-Fi scanning has visible loading animation/state.
- Button says `Confirm`.
- App does not attempt to read saved iPhone Wi-Fi password.
- App still asks for Wi-Fi password.
- After credentials are sent, app waits for device online status.
- App automatically navigates to dashboard once device is online.
- Timeout/error state is user-friendly.

### Backend Acceptance Criteria

- iOS app can check whether device is online.
- Polling behavior is stable.
- Timeout is handled cleanly.
- No unnecessary large API redesign.

### QA Acceptance Criteria

- Full provisioning flow works on real hardware.
- Failed Wi-Fi password case is handled.
- BLE disconnect case is handled.
- Provisioning timeout case is handled.
- Device can return to normal mode after failure.
- Device can successfully provision again after failure.
- No unrelated code changes.

---

## Test Cases

### Happy Path

1. User long-presses device button.
2. Device enters provisioning mode.
3. iOS app connects over BLE.
4. User selects Wi-Fi SSID.
5. User enters password.
6. User taps `Confirm`.
7. App sends credentials over BLE.
8. Device connects to Wi-Fi.
9. Device reports online to backend.
10. App navigates to dashboard.

Expected result:

```text
Provisioning succeeds and user lands on device dashboard.
```

### Device Busy Case

1. Device is doing scheduled task or backend retry.
2. User long-presses button.
3. Device enters provisioning mode.

Expected result:

```text
Provisioning starts anyway. Lower-priority tasks are paused or deferred.
```

### Wrong Wi-Fi Password

1. User enters wrong password.
2. Device fails to connect Wi-Fi.

Expected result:

```text
App shows friendly failure message and allows retry.
Device exits or remains safely retryable without getting stuck.
```

### BLE Disconnect

1. iOS app connects over BLE.
2. BLE disconnects before credentials are sent.

Expected result:

```text
App shows reconnect/retry option.
Device remains in provisioning mode until timeout or reconnect.
```

### Timeout

1. User enters provisioning mode.
2. No app connects.

Expected result:

```text
Device exits provisioning mode after timeout and resumes normal tasks.
```

### Online Detection Timeout

1. Credentials are sent.
2. Device does not appear online within timeout.

Expected result:

```text
App shows helpful error and retry option.
```

---

## Non-Goals

- Do not redesign the entire provisioning architecture.
- Do not add QR-code provisioning back.
- Do not add location field back.
- Do not implement Wi-Fi password extraction from iOS.
- Do not store Wi-Fi password permanently unless secure storage already exists.
- Do not refactor unrelated camera/backend/upload logic.
- Do not change production authentication unless directly required for this flow.

---
