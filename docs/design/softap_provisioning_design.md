# PlantLab SoftAP Provisioning README

## Goal

Implement a **SoftAP-based onboarding flow** for PlantLab devices running on Raspberry Pi.

This is the provisioning method for the current prototype phase. The purpose is to let a non-technical user connect a new device to home Wi-Fi and register it to their PlantLab account without SSH, file editing, or manual token entry into the OS.

This design should keep the **platform and backend model stable**, so that later the transport method can be changed from **SoftAP** to **BLE** when the hardware moves to ESP32.

---

## High-Level Strategy

Separate these two ideas:

1. **Transport method**: how setup data gets into the device
   - Current version: SoftAP
   - Future version: BLE

2. **Provisioning data model**: what setup data is exchanged
   - This should stay mostly the same even if the transport method changes later.

For the current version:
- The device starts in **SoftAP mode** if it is not provisioned.
- The user connects their phone or laptop to the device hotspot.
- The device serves a local provisioning web page.
- The user enters home Wi-Fi credentials and a platform-generated claim token.
- The device joins the home Wi-Fi.
- The device calls the PlantLab backend to register itself.
- The backend verifies the claim token and returns a long-term device access token.

---

## User Flow

### Main provisioning flow

1. User powers on a new PlantLab device.
2. Device starts a hotspot, for example:
   - SSID: `PlantLab-XXXX`
3. User opens phone or laptop Wi-Fi settings.
4. User connects to `PlantLab-XXXX`.
5. User opens the local setup page.
   - Example URL: `http://192.168.4.1`
6. On the PlantLab website, user clicks **Add Device**.
7. The website generates a short-lived **claim token**.
8. User enters on the device setup page:
   - home Wi-Fi SSID
   - home Wi-Fi password
   - claim token
9. Device saves the provisioning payload locally.
10. Device exits AP mode and attempts to connect to home Wi-Fi.
11. After network connection succeeds, the device calls the backend registration API.
12. Backend verifies the claim token and binds the device to the user account.
13. Backend returns a long-term device access token.
14. Device stores the device access token locally.
15. Device enters normal operating mode.

---

## Why SoftAP for v1

SoftAP is the correct choice for the current prototype because:
- It works well with Raspberry Pi.
- It is faster to build than BLE-based provisioning.
- It is easier to debug during hardware bring-up.
- It lets onboarding progress now without waiting for the future ESP32 redesign.

Known downsides:
- Users must leave their normal Wi-Fi temporarily.
- Some phones may warn that the hotspot has no internet.
- The flow is less polished than BLE commissioning.

These are acceptable tradeoffs for the current stage.

---

## Core Design Principle

The provisioning system must separate:

### Claiming a device
This is a **one-time action** that links a physical device to a PlantLab user account.

### Authenticating a device
This is the **long-term action** that lets the device securely talk to the backend after provisioning is complete.

Because of this, the system should use:
- a **temporary claim token** during onboarding
- a **long-term device access token** after registration succeeds

Do **not** use the temporary claim token as the device's permanent API credential.

---

## Required Data Model

## 1. Platform / backend must know

### User
Minimum fields:
- `user_id`
- `email`
- `name`
- `created_at`

### Device
Minimum fields:
- `device_id`
- `owner_user_id`
- `device_name`
- `status`
- `hardware_version`
- `software_version`
- `created_at`
- `last_seen_at`

Recommended `status` values:
- `unclaimed`
- `onboarding`
- `online`
- `offline`
- `error`

### Claim token
Minimum fields:
- `claim_token`
- `user_id`
- `created_at`
- `expires_at`
- `used_at`
- `used_by_device_id`

---

## 2. Device must know

### Permanent local fields
The device should store these locally:
- `device_id`
- `backend_url`
- `device_access_token`
- `hardware_version`
- `software_version`

### Provisioning-related local fields
The device may also store:
- `wifi_ssid`
- `wifi_password`
- provisioning state
- last provisioning error

The `device_id` must be stable and must not change across reboots.

---

## Provisioning Payload

This is the data submitted from the local setup page to the device.

### Example payload from local setup page to device

```json
{
  "ssid": "HomeWiFi",
  "password": "secret-password",
  "claim_token": "PL-ABC123XYZ",
  "backend_url": "https://api.plantlab.example"
}
```

### Notes
- `ssid` is required
- `password` may be empty for open networks, though home networks usually require a password
- `claim_token` is required
- `backend_url` can be hardcoded on the device in v1 if you prefer

---

## Registration Request to Backend

After the device joins home Wi-Fi successfully, it should call the backend.

### Example request

`POST /api/devices/register`

```json
{
  "device_id": "pl-device-0001",
  "claim_token": "PL-ABC123XYZ",
  "hardware_version": "rev_a",
  "software_version": "0.1.0",
  "capabilities": {
    "camera": true,
    "pump": true,
    "moisture_sensor": true,
    "light_control": true
  }
}
```

### Expected backend behavior
- verify claim token exists
- verify claim token has not expired
- verify claim token has not already been used
- bind `device_id` to the correct `user_id`
- mark token as used
- create or update device record
- return long-term device access token

### Example success response

```json
{
  "ok": true,
  "device_access_token": "long-lived-device-token",
  "device_name": "PlantLab Device",
  "status": "online"
}
```

### Example failure response

```json
{
  "ok": false,
  "error": "invalid_or_expired_claim_token"
}
```

---

## Device Local Storage Example

Example local JSON config stored on the Raspberry Pi:

```json
{
  "device_id": "pl-device-0001",
  "backend_url": "https://api.plantlab.example",
  "wifi_ssid": "HomeWiFi",
  "wifi_password": "secret-password",
  "device_access_token": "long-lived-device-token",
  "hardware_version": "rev_a",
  "software_version": "0.1.0",
  "provisioning_state": "online"
}
```

For v1, a local JSON file is acceptable if permissions are handled reasonably.

---

## Device State Machine

Use a simple explicit state machine.

Recommended states:
- `factory_reset`
- `ap_mode`
- `credentials_received`
- `wifi_connecting`
- `backend_registering`
- `online`
- `error`

### State meanings

#### `factory_reset`
- No Wi-Fi credentials stored
- No valid device access token stored
- Device should transition to `ap_mode`

#### `ap_mode`
- Device runs SoftAP
- Device runs local provisioning web server
- Waits for provisioning payload

#### `credentials_received`
- Device has received SSID/password/claim token
- Data should be validated and stored temporarily

#### `wifi_connecting`
- Device stops AP mode
- Device attempts to connect to the provided Wi-Fi network

#### `backend_registering`
- Device has network connectivity
- Device sends registration request to backend

#### `online`
- Device has valid device access token
- Device enters normal operation

#### `error`
- Provisioning or registration failed
- Device should expose enough information for retry or recovery

---

## Error Handling Requirements

The provisioning flow should handle these cases cleanly:

### 1. Wrong Wi-Fi password
- Device cannot join Wi-Fi
- Device should eventually return to `ap_mode`
- Local page should display a retry message if possible

### 2. Invalid or expired claim token
- Device joins Wi-Fi successfully
- Backend registration fails
- Device should either:
  - keep Wi-Fi and request a new claim token flow, or
  - reset back to AP mode with a clear error state

### 3. Backend unreachable
- Device has Wi-Fi but cannot reach backend
- Device should retry a limited number of times
- Then surface an error and/or re-enter provisioning recovery state

### 4. Reboot during provisioning
- Device should resume from stored provisioning state when possible
- Avoid corrupting config if power is lost mid-flow

---

## Security Notes for v1

This is still a prototype, but follow these minimum rules:

- Claim tokens should be short-lived.
- Claim tokens should be one-time-use.
- Do not keep the claim token as the permanent device credential.
- Device access tokens should be different from claim tokens.
- Store local config with restricted file permissions.
- Use HTTPS for backend API calls.

Possible later improvements:
- encrypt local credential storage
- signed QR or signed claim data
- device certificates
- per-device manufacturing secret

---

## Reset / Re-Provisioning Requirements

The device should support factory reset.

Factory reset should:
- delete stored Wi-Fi credentials
- delete stored device access token
- clear provisioning state
- restart into `ap_mode`

This is important for:
- testing
- ownership transfer
- support recovery

---

## UX Requirements for the Local Setup Page

The local setup page should be simple and mobile-friendly.

### Minimum fields
- Wi-Fi SSID
- Wi-Fi password
- claim token

### Minimum actions
- submit provisioning info
- show connecting status
- show success or failure

### Nice-to-have improvements
- scan for nearby SSIDs and show them in a dropdown
- show password toggle
- inline validation
- retry button
- automatic redirect or instructions after success

---

## Scope for Codex Implementation

The implementation work can be split into these pieces.

### 1. Raspberry Pi device provisioning service
Responsibilities:
- detect whether device is provisioned
- start/stop SoftAP
- serve local web UI
- accept provisioning payload
- write local config
- connect to Wi-Fi
- call backend registration API
- persist device access token
- expose status/logging

### 2. PlantLab backend onboarding APIs
Responsibilities:
- generate claim token for logged-in user
- store claim token with expiration
- validate device registration request
- bind device to user
- issue long-term device access token

### 3. PlantLab website Add Device flow
Responsibilities:
- logged-in user clicks Add Device
- website requests claim token from backend
- website displays claim token clearly
- website explains how to connect to `PlantLab-XXXX`
- later versions may show QR or richer instructions

---

## Recommended Implementation Order

1. Define backend endpoints and claim token model.
2. Build Raspberry Pi local provisioning service.
3. Build local setup page.
4. Implement Wi-Fi connection logic.
5. Implement backend device registration.
6. Add recovery and reset behavior.
7. Polish UX and logging.

---

## Future Migration to ESP32

When the hardware changes to ESP32, the provisioning transport can change from:
- SoftAP only

to:
- BLE primary
- SoftAP fallback

The following should remain mostly unchanged:
- device data model
- claim token flow
- backend registration API
- long-term device access token model
- device ownership logic

That is why this README keeps the provisioning data model independent from the current transport method.

---

## Summary

For PlantLab v1, use this pattern:

- Raspberry Pi device boots into SoftAP if unprovisioned
- local web page collects Wi-Fi credentials and claim token
- device joins home Wi-Fi
- device registers with backend
- backend returns long-term device access token
- device becomes online and enters normal operation

This is the correct practical solution for the current prototype stage.
