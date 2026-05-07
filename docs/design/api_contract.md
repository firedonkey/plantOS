# PlantLab API Contract

The device app and platform app communicate over HTTP. The device app should not import platform code, and the platform app should not import Raspberry Pi hardware code.

## Sensor Data

`POST /api/data`

```json
{
  "device_id": 1,
  "moisture": 42.5,
  "temperature": 22.2,
  "humidity": 51.0,
  "light_on": true,
  "pump_on": false,
  "pump_status": "not_needed",
  "timestamp": "2026-04-12T12:00:00+00:00"
}
```

Auth:

- signed-in owner browser session
- device API token header: `X-Device-Token`

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
- light: `on`, `off`

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
  "message": "pump ran for 5 seconds"
}
```

Acknowledgement statuses:

- `completed`
- `failed`
