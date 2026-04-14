# 📷🔐 PlantLab — QR-Based Device Provisioning PRD (No Hotspot)

## 1. Overview

This document defines a **QR-based onboarding system** for PlantLab devices.

Goal:
Allow users to fully set up a device by:

* scanning a QR code with the device camera
* without hotspot setup
* without manual token entry

👉 “Scan once → everything is configured”

---

## 2. Problem

Traditional onboarding:

* requires hotspot setup
* requires manual input (Wi-Fi, tokens)
* confusing for non-technical users

---

## 3. Solution

Use **camera-based QR provisioning**:

* Website generates a QR code
* Raspberry Pi scans QR
* QR contains:

  * Wi-Fi credentials
  * onboarding token
* Device auto-configures and registers

---

## 4. Goals

* zero manual input on device
* no hotspot required
* fast onboarding (<30 seconds)
* secure pairing with user account

---

## 5. Non-Goals (V1)

* mobile app scanning
* BLE provisioning
* advanced encryption (basic security only)

---

# 🧩 PART 1 — User Flow

---

## Step 1 — Device Boot

Device checks:

* if NOT provisioned → enter **QR Scan Mode**

---

## Step 2 — User Starts Setup

User:

* logs into website
* clicks **Add Device**

---

## Step 3 — QR Code Generated

Backend generates:

* short-lived onboarding token

Frontend displays QR code.

---

## Step 4 — User Shows QR to Device

User:

* holds laptop/phone screen in front of device camera

---

## Step 5 — Device Scans QR

Device:

* captures frames
* detects QR
* parses payload

---

## Step 6 — Device Connects to Wi-Fi

Device:

* extracts SSID + password
* writes to Wi-Fi config
* connects to network

---

## Step 7 — Device Registers with Backend

Device sends:

```json
{
  "device_id": "plab_001",
  "device_secret": "xxx",
  "onboarding_token": "abc123"
}
```

---

## Step 8 — Backend Response

Backend:

* verifies token
* links device to user
* returns:

```json
{
  "access_token": "jwt_token",
  "config": {}
}
```

---

## Step 9 — Setup Complete

Device:

* stores token
* enters normal operation

---

# 🧩 PART 2 — QR Payload Design

---

## Payload Format (JSON)

```json
{
  "version": 1,
  "ssid": "HomeWifi",
  "password": "MyPassword123",
  "onboarding_token": "abc123xyz",
  "backend_url": "https://api.plantlab.com",
  "expires_at": "2026-04-13T18:30:00Z"
}
```

---

## Encoding

* JSON → string
* optionally base64 encode

---

## Constraints

* QR must be scannable from screen
* payload size should be minimized

---

# 🧩 PART 3 — Device Behavior

---

## QR Scan Mode

Device:

* activates camera
* scans continuously
* validates QR payload

---

## Validation

Device checks:

* required fields present
* not expired
* valid format

---

## Wi-Fi Setup

Device:

* writes credentials to config
* example:

```bash
/etc/wpa_supplicant/wpa_supplicant.conf
```

* restarts network

---

## Backend Registration

Device:

* sends onboarding request
* retries if failure

---

## Storage

Device stores:

* access_token
* Wi-Fi credentials
* backend URL

---

# 🧩 PART 4 — Backend Design

---

## Generate QR

```text
POST /api/device/onboarding-token
```

Response:

* onboarding_token
* expiration time

---

## Register Device

```text
POST /api/device/register
```

---

## Validation Rules

* onboarding_token must:

  * be valid
  * not expired
  * not used before

---

## State Update

Device:

* unclaimed → claimed → active

---

# 🧩 PART 5 — Data Model

---

## Device

```text
device_id
device_secret
user_id
status
```

---

## Onboarding Token

```text
token
user_id
expires_at
used (boolean)
```

---

# 🧩 PART 6 — Security

---

## Rules

* onboarding_token expires in 5–10 minutes
* token is one-time use
* device_secret never exposed
* HTTPS required

---

## Risks

* Wi-Fi password in QR
* screen visibility

---

## Mitigation (V1)

* short-lived QR
* user authentication required
* optional obfuscation

---

# 🧩 PART 7 — Device Requirements

---

Device must:

* support camera capture
* detect QR codes
* parse JSON payload
* configure Wi-Fi
* connect to backend
* store tokens securely

---

# 🧩 PART 8 — UX Design

---

## Setup Page

Display:

* large QR code
* instructions:

```text
1. Power on device
2. Point camera at QR code
3. Wait for connection
```

---

## Status Feedback

Show:

* waiting for scan
* device connected
* setup complete

---

# 🧩 PART 9 — Edge Cases

---

* QR not detected → retry
* Wi-Fi wrong → reconnect flow
* token expired → regenerate QR
* backend unreachable → retry

---

# 🧩 PART 10 — Implementation Plan

---

## Phase 1

* backend token API
* QR generation

## Phase 2

* device QR scanning
* Wi-Fi config

## Phase 3

* backend registration

## Phase 4

* UX polish

---

# 🧠 Key Principle

👉 One QR scan handles:

* Wi-Fi setup
* device pairing
* authentication

---

# 🚀 First Task for Codex

Implement:

1. QR payload generator (backend)
2. onboarding token API
3. QR scanning module (Pi)
4. Wi-Fi config logic
5. device registration API

Keep implementation modular and production-ready.
