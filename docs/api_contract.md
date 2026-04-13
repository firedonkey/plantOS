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

Future device command flow:

1. Platform stores a pending command for a device.
2. Device polls platform for pending commands.
3. Device executes the command locally.
4. Device acknowledges completion or failure.
