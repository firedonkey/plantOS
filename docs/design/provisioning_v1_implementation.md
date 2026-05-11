# PlantLab v1 SoftAP Provisioning

This document summarizes the complete v1 implementation aligned with [SoftAP Provisioning Design](/Users/gary/plantOS/docs/design/softap_provisioning_design.md).

## Folder Structure

```text
plantOS/
  docs/design/softap_provisioning_design.md

  device/
    provision.py
    config.yaml
    provisioning/
      README.md
      __init__.py
      backend.py
      device_identity.py
      network.py
      service.py
      state.py
      storage.py
      web.py
      wifi.py

  provision_backend/
    .env.example
    package.json
    README.md
    src/
      app.js
      config.js
      db/
        pool.js
        provisioning_schema.sql
      frontend/
        components/
          AddDevicePage.jsx
        lib/
          deviceClaimApi.js
        styles/
          add-device.css
      lib/
        errors.js
        tokens.js
      middleware/
        devAuth.js
        requireAuthenticatedUser.js
      models/
        provisioningSchemas.js
      routes/
        devices.js
      services/
        deviceProvisioningService.js
```

## System Flow

1. Logged-in user opens the website Add Device page.
2. Website calls `POST /api/devices/claim-token`.
3. Backend creates a short-lived one-time claim token.
4. Device boots unprovisioned and enters `ap_mode`.
5. User connects to `PlantLab-XXXX`.
6. User opens `http://192.168.4.1`.
7. Local Flask page collects Wi-Fi SSID, Wi-Fi password, claim token, and backend URL.
8. Device stores the provisioning payload locally.
9. Device stops SoftAP and connects to home Wi-Fi.
10. Device calls `POST /api/devices/register`.
11. Backend validates the claim token and binds the device to the token owner.
12. Backend returns a long-term `device_access_token`.
13. Device saves the long-term token locally and enters `online`.

## Backend API Code

- `provision_backend/src/routes/devices.js`
- `provision_backend/src/services/deviceProvisioningService.js`
- `provision_backend/src/db/provisioning_schema.sql`

Endpoints:

```http
POST /api/devices/claim-token
POST /api/devices/register
```

## Website Add Device Page

- `provision_backend/src/frontend/components/AddDevicePage.jsx`
- `provision_backend/src/frontend/lib/deviceClaimApi.js`
- `provision_backend/src/frontend/styles/add-device.css`

The page calls:

```http
POST /api/devices/claim-token
```

with cookie credentials included.

## Raspberry Pi Device Service

- `device/provision.py`
- `device/provisioning/service.py`
- `device/provisioning/web.py`
- `device/provisioning/wifi.py`
- `device/provisioning/backend.py`
- `device/provisioning/storage.py`

State machine:

```text
factory_reset
ap_mode
credentials_received
wifi_connecting
backend_registering
online
error
```

## Config Examples

### Device Config

```yaml
provisioning:
  backend_url: https://marspotatolab.com
  state_file: data/provisioning/device_config.json
  network_dry_run: true
  hardware_version: raspberry_pi_3
  software_version: 0.1.0
  capabilities:
    camera: true
    pump: true
    moisture_sensor: true
    light_control: true
```

### Backend Env

```bash
PORT=3000
DATABASE_URL=postgresql://plantlab_user:change-me@localhost:5432/plantlab
CLAIM_TOKEN_TTL_MINUTES=15
DEVICE_ACCESS_TOKEN_BYTES=32
ENABLE_DEV_AUTH=true
DEV_AUTH_USER_ID=1
DEV_AUTH_EMAIL=dev@example.com
```

## Step-By-Step Local Test Plan

### 1. Prepare PostgreSQL

```bash
createdb plantlab
psql plantlab < provision_backend/src/db/provisioning_schema.sql
psql plantlab -c "insert into users (id, email, name) values (1, 'dev@example.com', 'Dev User') on conflict do nothing;"
```

### 2. Start Backend

```bash
cd provision_backend
npm install
ENABLE_DEV_AUTH=true \
DEV_AUTH_USER_ID=1 \
DATABASE_URL=postgresql://plantlab_user:change-me@localhost:5432/plantlab \
npm run dev
```

### 3. Create Claim Token

```bash
curl -X POST http://127.0.0.1:3000/api/devices/claim-token \
  -H "Content-Type: application/json" \
  -H "x-dev-user-id: 1" \
  -d '{}'
```

Copy `claim_token` from the response.

### 4. Start Device Provisioning Service In Dry Run

```bash
cd device
source ../.venv/bin/activate
python provision.py \
  --backend-url http://127.0.0.1:3000 \
  --port 8080 \
  --reset
```

Open:

```text
http://127.0.0.1:8080
```

Submit:

- SSID: `HomeWiFi`
- Password: any value
- Claim token: token from step 3
- Backend URL: `http://127.0.0.1:3000`

### 5. Verify Device Config

```bash
cat device/data/provisioning/device_config.json
```

Expected state:

```json
{
  "provisioning_state": "online",
  "device_access_token": "..."
}
```

### 6. Verify Database

```bash
psql plantlab -c "select device_id, owner_user_id, status from devices;"
psql plantlab -c "select claim_token, used_at, used_by_device_id from device_claim_tokens;"
```

## Assumptions

- Existing production auth will populate `req.user`.
- Local dev can use `ENABLE_DEV_AUTH=true`.
- PostgreSQL is available for the Node backend.
- Device-side dry-run mode is used until real Pi network commands are validated.
- `wpa_supplicant` is the first target for Wi-Fi configuration.
- SoftAP command setup is still stub-friendly.
- Device identity comes from `/etc/machine-id` when available.
- Backend URL can come from config, env, CLI, or local setup payload.

## TODOs

- Integrate Express routes into the production backend or decide if this remains a separate service.
- Add migrations for provisioning tables.
- Add backend tests for claim/register flows.
- Add React build tooling or mount `AddDevicePage` inside the current website.
- Replace dry-run SoftAP commands with tested `hostapd` and `dnsmasq` setup.
- Validate actual Raspberry Pi Wi-Fi behavior on your OS image.
- Add setup-page progress polling.
- Return to AP mode after Wi-Fi failure.
- Add backend registration retry/backoff.
- Encrypt or protect local Wi-Fi credentials.
- Add factory reset button support.
- Add systemd services for boot-time provisioning.
