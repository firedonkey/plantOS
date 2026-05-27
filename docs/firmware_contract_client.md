# Firmware Contract Client

The ESP32 firmware now has a small contract helper layer under
`device/esp32/src/contracts/`. It is intentionally an adapter over the existing
firmware architecture.

Current flow:

1. The master node polls `GET /api/hardware/commands/poll` with
   `hardware_device_id`, `node_role`, `firmware_version`, `schema_version`, and
   `hardware_model`.
2. If the contract poll fails, firmware falls back to legacy
   `/api/hardware/commands/pending`.
3. Contract `COMMAND` envelopes are parsed into the existing `PlatformCommand`
   shape.
4. Firmware sends a `COMMAND_RESULT` envelope with `status: "acked"` before
   long work starts.
5. Firmware sends a second result envelope for `completed`, `failed`, or
   `rejected`.
6. Firmware heartbeat reporting sends `HEARTBEAT` envelopes with actuator and
   runtime state when required fields are available.
7. OTA status reporting first sends `OTA_STATUS` envelopes and falls back to the
   legacy OTA status payload when needed.

Implemented command adapters:

- `SET_LIGHT_BRIGHTNESS` -> existing grow LED intensity handler
- `CAPTURE_IMAGE` -> existing ESP-NOW camera capture handler
- `REQUEST_DIAGNOSTICS` -> existing heartbeat/diagnostics upload path
- `START_OTA` -> existing OTA manager through `OtaStartRequest`

Unsupported command types are rejected explicitly with a contract error code.
This is safer than treating future commands as legacy actions.

`START_OTA` flow:

1. Firmware receives a contract `COMMAND` with `command_type: "START_OTA"`.
2. Firmware ACKs the command immediately.
3. Firmware validates `target_version`, `download_url`, optional
   `checksum_sha256`, and optional `hardware_model`.
4. Firmware rejects the command if the artifact URL is not backend-owned.
5. Firmware reports `COMMAND_RESULT` `in_progress`.
6. The OTA manager emits `OTA_STATUS` envelopes for preparing, downloading,
   validating, installing, rebooting, success, or failed.
7. On reboot into the new firmware version, pending OTA preferences are used to
   report `OTA_STATUS` success and final `COMMAND_RESULT` completed.

Accepted artifact URLs:

- `/api/hardware/ota/artifacts/{release_id}`
- The same path prefixed by the configured backend base URL

Rejection cases:

- missing `target_version`
- missing `download_url`
- `hardware_model` does not match this firmware build
- malformed `checksum_sha256`
- OTA already in progress
- non-backend-owned artifact URL

Memory/runtime notes:

- Command polling uses a bounded `StaticJsonDocument<4096>`.
- Heartbeat envelopes use a bounded `StaticJsonDocument<1536>`.
- Command result and OTA status envelopes use bounded
  `StaticJsonDocument<768>`.
- Unknown additive fields are ignored by the parser.
- Unsupported schema major versions are rejected before dispatch.
- There is no durable offline queue yet.

Heartbeat state:

- `actuators.ambient_light.enabled` reports the current grow LED state.
- `actuators.ambient_light.brightness_percent` is included when PWM intensity
  control is enabled.
- `runtime.capture_interval_seconds` reports the configured camera capture
  interval.
- `runtime.ota_status` reports the OTA manager's current known state.
- `runtime.provisioning_status` reports the firmware provisioning state.
- `runtime.camera_node_status` is included only when the master has observed
  camera runtime/provisioning state.
- `runtime.last_command_id` and `runtime.last_command_status` are included
  after the first command result is recorded.

Current limitations:

- `REBOOT`, `ENTER_PAIRING_MODE`, `FACTORY_RESET`, and
  `UPDATE_CAPTURE_INTERVAL` are parsed but rejected until product behavior is
  finalized.
- Timestamps in firmware-generated envelopes are boot-relative placeholders
  until NTP is guaranteed.

Future work:

- Add a bounded retry queue for result envelopes if network loss occurs during
  command completion.
- Add camera-node contract polling once the camera node moves beyond heartbeat
  and image upload reporting.
