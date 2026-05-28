# PlantLab Device Protocol

PlantLab now has a contract-first JSON protocol foundation. The source of truth
lives in `contracts/`.

Current migration slice:

- Shared JSON Schema files for the base envelope, heartbeat, diagnostics, commands, command results, OTA status, and canonical events.
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

Current backend ingestion:

- `POST /api/hardware/heartbeat` accepts legacy heartbeat JSON and new `HEARTBEAT` envelopes.
- `POST /api/hardware/heartbeat` still accepts legacy embedded diagnostics.
- `POST /api/hardware/diagnostics` accepts new `DIAGNOSTICS` envelopes.
- Current mobile/web command APIs still create legacy command rows.
- `GET /api/hardware/commands/poll` returns contract-native `COMMAND` envelopes.
- `POST /api/hardware/commands/{id}/result` accepts legacy command results and new `COMMAND_RESULT` envelopes.
- `POST /api/hardware/ota/status` accepts legacy OTA status JSON and new `OTA_STATUS` envelopes.
- `GET /api/devices/{id}/timeline` exposes canonical device events with
  summaries, filters, and cursor pagination for diagnostics.
- Heartbeat, diagnostics, command results, and OTA status ingestion derive
  state-change events when meaningful values change.

Current firmware support:

- Master firmware can poll `GET /api/hardware/commands/poll` for typed
  `COMMAND` envelopes.
- Master firmware sends contract `HEARTBEAT` envelopes with optional
  `hardware_model`, `hardware_version`, `actuators`, and `runtime` fields.
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

Future phases will migrate provisioning and image upload.

Heartbeat v1 additive state:

- `actuators.ambient_light.enabled` and `brightness_percent` represent the grow
  LED state.
- `runtime.capture_interval_seconds`, `ota_status`, `provisioning_status`,
  `camera_node_status`, `last_command_id`, `last_command_status`,
  `time_sync_status`, and `last_ntp_sync_at` are optional runtime details.
  Firmware omits fields that are not known.
- The backend stores the full contract heartbeat payload in the canonical
  `HEARTBEAT_RECEIVED` event data and maps ambient light state into the current
  device status for existing dashboards.
- The backend compares heartbeat state against the latest canonical heartbeat
  for the same hardware node to emit actuator, camera-node, OTA runtime, device
  health, and Wi-Fi signal state-change events.
- RSSI state uses hysteresis: degraded at `<= -80 dBm`, recovered at
  `>= -70 dBm`.
