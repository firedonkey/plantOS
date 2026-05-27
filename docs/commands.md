# Command Protocol

PlantLab command contracts define backend-to-device commands and device-to-backend
command results. The current implementation is an adapter over the existing
`commands` table and legacy firmware polling routes.

Lifecycle:

```text
queued -> sent -> acked -> in_progress -> completed
                         -> failed
                         -> timed_out
                         -> rejected
```

Supported v1 command types:

- `SET_LIGHT_BRIGHTNESS`
- `CAPTURE_IMAGE`
- `REBOOT`
- `START_OTA`
- `ENTER_PAIRING_MODE`
- `FACTORY_RESET`
- `REQUEST_DIAGNOSTICS`
- `UPDATE_CAPTURE_INTERVAL`

Command envelope:

```json
{
  "schema_version": "1.0",
  "message_id": "cmdmsg_01HX...",
  "device_id": 33,
  "hardware_device_id": "pl-esp32-64e0a80af6e8",
  "node_role": "master",
  "message_type": "COMMAND",
  "sent_at": "2026-05-27T12:00:00Z",
  "payload": {
    "command_id": "cmd_123",
    "command_type": "CAPTURE_IMAGE",
    "target": {
      "node_role": "camera",
      "hardware_device_id": "pl-cam-1c1df816a398"
    },
    "params": {
      "reason": "manual"
    },
    "timeout_ms": 120000,
    "retry_policy": {
      "max_attempts": 3,
      "backoff_ms": 3000
    },
    "priority": "normal",
    "scheduled_for": null
  }
}
```

Command result envelope:

```json
{
  "schema_version": "1.0",
  "message_id": "cmdresmsg_01HX...",
  "device_id": 33,
  "hardware_device_id": "pl-cam-1c1df816a398",
  "node_role": "camera",
  "message_type": "COMMAND_RESULT",
  "sent_at": "2026-05-27T12:00:10Z",
  "payload": {
    "command_id": "cmd_123",
    "command_type": "CAPTURE_IMAGE",
    "status": "completed",
    "message": "image uploaded",
    "result": {
      "image_id": 991,
      "upload_ms": 1836
    },
    "error_code": null
  }
}
```

Current backend behavior:

- Existing mobile/web command APIs continue to create legacy `Command` rows.
- The backend builds contract-style command payloads internally for supported commands.
- Existing firmware can keep polling legacy command JSON.
- New firmware can poll `GET /api/hardware/commands/poll` for typed command envelopes.
- Devices may report legacy command results to `/api/hardware/commands/{id}/result`.
- Devices may also report `COMMAND_RESULT` envelopes to the same result endpoint.
- Canonical command lifecycle events are stored in `device_diagnostic_events`.

Contract-native polling:

```text
GET /api/hardware/commands/poll?hardware_device_id=master-01&node_role=master&firmware_version=1.2.0&schema_version=1.0
```

Response:

```json
{
  "schema_version": "1.0",
  "commands": []
}
```

When a command is returned by this endpoint:

- The backend marks the command `sent`.
- The backend emits `COMMAND_POLLED` and `COMMAND_SENT`.
- Firmware should respond with a `COMMAND_RESULT` envelope using `status:
  "acked"` as soon as it accepts the command.
- Completion or failure should be reported with a second `COMMAND_RESULT`
  envelope.

Current filtering:

- Master commands are returned to master nodes.
- Camera commands are returned to camera nodes.
- Master nodes may also receive camera commands while the current ESP-NOW
  gateway topology remains active.
- Firmware below the contract poll minimum receives an empty command list and
  can continue using legacy polling.
- Unsupported legacy commands are skipped for contract polling and remain
  available to legacy polling.

Future phases:

- Add a public/admin backend API that creates `START_OTA` command rows using
  the params from `docs/ota.md`.
- Firmware contract helpers now poll the contract endpoint first and fall back
  to legacy polling if the new endpoint or schema validation fails.
- Add command scheduling after the base command lifecycle is stable.
- Add exponential retry, offline buffering, websocket push, or MQTT transport
  only after the polling protocol is stable.
