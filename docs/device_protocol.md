# PlantLab Device Protocol

PlantLab now has a contract-first JSON protocol foundation. The source of truth
lives in `contracts/`.

Current migration slice:

- Shared JSON Schema files for the base envelope, heartbeat, diagnostics,
  commands, command results, OTA status, image upload reporting, and canonical
  events.
- Hand-written Pydantic models that mirror the schemas.
- Mirrored TypeScript types for web/mobile.
- ESP32-friendly string constants.
- Backend acceptance for both legacy payloads and new contract envelopes.

New device messages use this envelope:

```json
{
  "schema_version": "1.0",
  "message_id": "evt_01HX...",
  "device_id": 33,
  "hardware_device_id": "pl-esp32-64e0a80af6e8",
  "node_role": "master",
  "message_type": "HEARTBEAT",
  "sent_at": "2026-05-27T12:00:00Z",
  "payload": {}
}
```

Rules:

- New firmware should include the envelope.
- `sent_at` is recommended on every envelope. Backend validation tolerates it
  being missing during early boot, but current firmware sends an epoch fallback
  before NTP sync and real UTC after sync.
- Existing firmware may continue sending legacy heartbeat payloads during migration.
- The backend accepts additive unknown fields on new contract messages and logs a warning.
- The backend rejects unsupported major schema versions.
- Keep payloads flat and small for ESP32 memory safety.

Implemented message types:

- `HEARTBEAT`
- `DIAGNOSTICS`
- `COMMAND`
- `COMMAND_RESULT`
- `OTA_STATUS`
- `IMAGE_UPLOAD`

Current backend ingestion:

- `POST /api/hardware/heartbeat` accepts legacy heartbeat JSON and new `HEARTBEAT` envelopes.
- `POST /api/hardware/heartbeat` still accepts legacy embedded diagnostics.
- `POST /api/hardware/diagnostics` accepts new `DIAGNOSTICS` envelopes.
- Current mobile/web command APIs still create legacy command rows.
- `GET /api/hardware/commands/poll` returns contract-native `COMMAND` envelopes.
- `POST /api/hardware/commands/{id}/result` accepts legacy command results and new `COMMAND_RESULT` envelopes.
- `POST /api/hardware/ota/status` accepts legacy OTA status JSON and new `OTA_STATUS` envelopes.
- `POST /api/image` still accepts legacy multipart image uploads. New firmware
  and the simulator may include an `IMAGE_UPLOAD` envelope in the multipart
  `metadata` form field. Camera uploads may also include `camera_node_id` and
  `camera_role` (`top` or `side`) form fields.
- `POST /api/hardware/image-upload/report` accepts `IMAGE_UPLOAD` envelopes for
  upload failures or upload-complete reports that do not carry the image binary.
- `GET /api/devices/{id}/timeline` exposes canonical device events with
  summaries, filters, and cursor pagination for diagnostics.
- Heartbeat, diagnostics, command results, OTA status, setup status, and image
  ingestion derive lifecycle/state-change events when meaningful values change.

Current firmware support:

- Master firmware can poll `GET /api/hardware/commands/poll` for typed
  `COMMAND` envelopes.
- Master firmware sends contract `HEARTBEAT` envelopes with optional
  `hardware_model`, `hardware_version`, `actuators`, and `runtime` fields.
- Master firmware accepts `SET_AMBIENT_LED_BELT` commands for the WS2811 ambient LED belt on
  the master board. Params mirror the backend command `value` JSON object.
- Camera firmware includes `camera_role` in registration and heartbeat payloads
  when the node has been provisioned as `top` or `side`.
- Firmware attempts non-blocking SNTP after Wi-Fi connection and uses UTC
  ISO8601 `sent_at` timestamps after synchronization.
- NTP servers and retry timing are firmware build-time configuration values;
  defaults are `pool.ntp.org`, `time.google.com`, 15 seconds per attempt, and a
  five-minute retry interval.
- Master firmware sends `COMMAND_RESULT` envelopes for acknowledged, completed,
  failed, and rejected contract commands.
- OTA status reporting emits `OTA_STATUS` envelopes first and falls back to the
  legacy OTA status payload.
- Legacy command polling and legacy result reporting remain as fallback paths.

Provisioning contract payloads are still a future phase, but setup status now
emits canonical provisioning lifecycle events:

- `PROVISIONING_STARTED`
- `PROVISIONING_SUCCESS`
- `PROVISIONING_FAILED`

Image upload v1 metadata:

- `status` is `uploaded` or `failed`.
- Uploaded metadata may include `image_id`, `source_hardware_device_id`,
  `source_node_role`, `camera_node_id`, `camera_role`, `captured_at`,
  `upload_reason`, `width`, `height`, `content_type`, and `upload_ms`.
- Failed metadata must include `failure_reason`.
- The backend keeps actual image storage unchanged and emits
  `IMAGE_CAPTURE_STARTED`, `IMAGE_CAPTURED`, `IMAGE_UPLOAD_STARTED`,
  `IMAGE_UPLOADED`, and `IMAGE_UPLOAD_FAILED` canonical events from command
  requests and validated metadata.

Heartbeat v1 additive state:

- `actuators.grow_light.enabled` and `brightness_percent` represent the grow-light
  state. Older firmware may still send `actuators.ambient_light`; the backend
  accepts it only as a legacy alias.
- `runtime.capture_interval_seconds`, `ota_status`, `provisioning_status`,
  `camera_node_status`, `last_command_id`, `last_command_status`,
  `last_command_poll_at`, `last_command_poll_status`,
  `last_command_poll_error`, `last_command_poll_latency_ms`,
  `command_poll_stale_seconds`, `time_sync_status`, and `last_ntp_sync_at` are
  optional runtime details. Firmware omits fields that are not known.
- `runtime.ambient_led_belt` reports WS2811 ambient LED belt state when available:
  `available`, `enabled`, `mode`, `brightness`, `max_brightness`, `color`,
  `logical_pixel_count`, `physical_led_count`, `color_order`, `data_gpio`,
  `diagnostic_active`, and optional `last_error`.
- The backend stores the full contract heartbeat payload in the canonical
  `HEARTBEAT_RECEIVED` event data and maps grow-light state into the current
  device status for existing dashboards.
- The backend compares heartbeat state against the latest canonical heartbeat
  for the same hardware node to emit actuator, camera-node, OTA runtime, device
  health, and Wi-Fi signal state-change events.
- RSSI state uses hysteresis: degraded at `<= -80 dBm`, recovered at
  `>= -70 dBm`.
- Command poll stale detection currently uses heartbeat runtime telemetry and
  emits `COMMAND_POLL_STALE` when `command_poll_stale_seconds` crosses
  `>= 300`.

Ambient LED belt command params:

```json
{
  "mode": "solid",
  "enabled": true,
  "brightness": 26,
  "color": {"r": 255, "g": 0, "b": 0},
  "logical_pixel_count": 14,
  "color_order": "RGB"
}
```

Accepted modes are `off`, `solid`, `breathe`, `pulse`, `chase`, `rainbow`, and
`diagnostic`. Optional fields are `speed_ms`, `maximum_brightness`,
`default_brightness`, `save_config`, and `cancel_diagnostic`. Firmware clamps
runtime brightness to the configured maximum and rejects invalid config or speed
fields before applying an idempotent command.
