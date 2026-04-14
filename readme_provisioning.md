# 🔐🌐 PlantLab — Device Provisioning & Wi-Fi Onboarding PRD

## 1. Overview

This document defines the device onboarding and Wi-Fi provisioning system for PlantLab.

Goal:
Enable **non-technical users** to:

1. connect the device to Wi-Fi
2. claim the device to their account

👉 without using command line, SSH, or manual token entry.

---

## 2. Problem

### Current Issues

* Requires manual token entry into Raspberry Pi
* Requires technical knowledge (SSH, config files)
* No user-friendly Wi-Fi setup

---

## 3. Solution

Split onboarding into **two independent flows**:

### Flow A — Wi-Fi Provisioning

Device helps user connect it to internet.

### Flow B — Device Claiming

User links device to their account.

---

## 4. Goals

* No manual token entry
* No command line usage
* Works for non-technical users
* Scalable to multiple devices

---

## 5. Non-Goals (V1)

* Mobile app onboarding
* Bluetooth provisioning
* Advanced device permissions

---

# 🧩 PART 1 — Wi-Fi Provisioning

---

## 6. Wi-Fi Setup Flow (Hotspot Mode)

### Step 1 — Device Boot

Device checks:

```text
Is Wi-Fi configured?
```

If NO:
👉 enter **Hotspot Mode**

---

## Step 2 — Create Hotspot

Device creates Wi-Fi:

```text
PlantLab-Setup-XXXX
```

Where `XXXX` = last digits of device_id

---

## Step 3 — User Connects

User:

* opens phone/laptop Wi-Fi
* connects to hotspot

---

## Step 4 — Setup Page

User opens browser:

```text
http://192.168.4.1
```

OR captive portal auto-opens

---

## Step 5 — User Inputs Wi-Fi

Form:

```text
Wi-Fi Name (SSID)
Password
```

---

## Step 6 — Device Saves Config

Device:

* writes to Wi-Fi config
* example (Raspberry Pi):

```bash
/etc/wpa_supplicant/wpa_supplicant.conf
```

---

## Step 7 — Connect to Internet

Device:

* exits hotspot mode
* connects to home Wi-Fi

---

## Step 8 — Confirmation

Show message:

```text
Device connected successfully.
Now go to plantlab.com and add your device.
```

---

## 7. System Components (Pi)

* hostapd → hotspot
* dnsmasq → DHCP
* Flask/FastAPI → setup page

---

# 🧩 PART 2 — Device Claiming

---

## 8. Device Identity

Each device has:

* device_id
* claim_code (human-readable)
* device_secret (hidden)

---

## 9. Device States

| State     | Description       |
| --------- | ----------------- |
| unclaimed | not linked        |
| claimed   | linked to user    |
| active    | fully operational |

---

## 10. User Flow

---

### Step 1 — User Login

User logs into website.

---

### Step 2 — Add Device

User:

* clicks "Add Device"
* enters claim_code OR scans QR code

---

### Step 3 — Backend Validation

Backend checks:

* device exists
* claim_code matches
* device not already claimed

---

### Step 4 — Claim Success

Backend:

* links device to user
* updates state → claimed

---

## 11. Device Authentication

Device sends:

```json
{
  "device_id": "plab_001",
  "device_secret": "xxx"
}
```

Backend returns:

```json
{
  "access_token": "jwt_token"
}
```

---

## 12. Normal Operation

Device:

* uses access_token
* sends sensor data
* uploads images

---

# 🧩 PART 3 — Data Model

---

## Device Table

```text
id
device_id
device_secret
claim_code
user_id
status
created_at
```

---

## User Table

```text
id
email
password_hash
```

---

## Token Table

```text
id
device_id
access_token
expires_at
```

---

# 🧩 PART 4 — API Design

---

## Claim Device

```text
POST /api/device/claim
```

---

## Device Auth

```text
POST /api/device/auth
```

---

## Send Data

```text
POST /api/data
Authorization: Bearer token
```

---

# 🧩 PART 5 — Device Requirements

Device must:

* detect Wi-Fi status
* start hotspot if no Wi-Fi
* host setup web page
* store credentials
* authenticate with backend
* store access_token
* send data/images

---

# 🧩 PART 6 — Security

* claim_code = limited use
* device_secret never exposed
* HTTPS required
* tokens expire

---

# 🧩 PART 7 — Future Enhancements

* QR scanning
* mobile app onboarding
* BLE provisioning
* batch device onboarding (classroom)

---

# 🧩 PART 8 — Implementation Plan

---

## Phase 1

* backend APIs
* device identity model

## Phase 2

* device claim flow

## Phase 3

* hotspot Wi-Fi setup

## Phase 4

* UI improvements

---

# 🧠 Key Principle

👉 Device connects to internet first
👉 User claims device second
👉 Device receives token automatically

---

# 🚀 First Task for Codex

Implement:

1. Wi-Fi detection + hotspot mode logic
2. Setup web server on device
3. Device claim API
4. Device authentication API
5. Token system

Keep implementation modular and production-ready.
