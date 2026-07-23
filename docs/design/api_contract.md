# PlantLab API Contract

The device app and platform app communicate over HTTP. Device firmware should not import platform code, and the platform app should not import hardware-specific firmware code.

## Sensor Data

`POST /api/data`

```json
{
  "device_id": 1,
  "moisture": 42.5,
  "temperature": 22.2,
  "humidity": 51.0,
  "water_temperature_c": 19.8,
  "water_level_raw": 35120,
  "water_level_state": "ok",
  "light_on": true,
  "light_intensity_percent": 70,
  "pump_on": false,
  "pump_status": "not_needed",
  "timestamp": "2026-04-12T12:00:00+00:00"
}
```

Auth:

- signed-in owner browser session
- device API token header: `X-Device-Token`

Water sensor fields are optional for backwards compatibility. Current ESP32-S3 master nodes should send `water_temperature_c` from the MCP9808T-E/MS water-temperature sensor on I2C and `water_level_raw` from the bottom capacitive water-level pad's filtered touch reading. `water_level_state` is a short derived state such as `uncalibrated`, `empty`, `low`, `medium`, `high`, `inconsistent`, `sensor_unavailable`, or `unknown`.

Contract heartbeats may also include `payload.runtime.water_level` with the latest per-pad touch diagnostics, calibration thresholds, and debounce status.

## Image Upload

`POST /api/image`

Multipart form fields:

- `device_id`
- `file`

Accepted file types:

- `image/jpeg`
- `image/png`
- `image/webp`

Auth:

- signed-in owner browser session
- device API token header: `X-Device-Token`

## Commands

Owner creates a command:

`POST /api/devices/{device_id}/commands`

```json
{
  "target": "pump",
  "action": "run",
  "value": "5"
}
```

Supported commands:

- pump: `run`, `off`
- light: `on`, `off`, `set_intensity`

Light intensity commands use `target: "light"`, `action: "set_intensity"`, and a string `value` containing an integer percent from `0` through `100`. Owner-facing wrapper APIs may also send `POST /api/devices/{device_id}/commands/light` with `{"intensity_percent": 70}`. Clients should only expose intensity controls when a registered node advertises `light_intensity_control: true` or an equivalent `light_control_modes` entry.

Owner lists recent commands:

`GET /api/devices/{device_id}/commands`

Device polls pending commands:

`GET /api/devices/{device_id}/commands/pending`

Required header:

- `X-Device-Token`

The platform marks returned commands as `sent` so they are not sent repeatedly.

Device acknowledges a command:

`POST /api/devices/{device_id}/commands/{command_id}/ack`

```json
{
  "status": "completed",
  "message": "pump ran for 5 seconds",
  "light_intensity_percent": 70
}
```

Acknowledgement statuses:

- `completed`
- `failed`
