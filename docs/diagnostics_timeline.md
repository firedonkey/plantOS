# Diagnostics Timeline

The diagnostics timeline is the internal debugging view for per-device canonical
events. It is intentionally lightweight: one API query, concise summaries, and
expandable event details.

## API

`GET /api/devices/{id}/timeline`

Query parameters:

- `limit`: 1 to 100, default 50
- `before`: return events older than this timestamp
- `after`: return events at or after this timestamp
- `event_type`: repeatable event type filter
- `severity`: repeatable severity filter
- `node_role`: filters source or target node role
- `correlation_id`: filters a command/message correlation id

Response:

```json
{
  "events": [
    {
      "id": 123,
      "event_type": "COMMAND_ACKED",
      "severity": "info",
      "occurred_at": "2026-05-27T12:00:00Z",
      "hardware_device_id": "pl-esp32-64e0a80af6e8",
      "node_role": "master",
      "correlation_id": "cmd_01HX...",
      "summary": "CAPTURE_IMAGE acknowledged",
      "data": {}
    }
  ],
  "next_before": "2026-05-27T12:00:00Z"
}
```

## Summaries

The backend owns summary text so web/mobile clients do not duplicate event
interpretation. Examples:

- `HEARTBEAT_RECEIVED`: `Heartbeat received (RSSI -58 dBm)`
- `COMMAND_SENT`: `START_OTA sent to master node`
- `COMMAND_COMPLETED`: `CAPTURE_IMAGE completed`
- `OTA_DOWNLOADING`: `OTA downloading 42%`
- `OTA_FAILED`: `OTA failed: checksum mismatch`
- `ACTUATOR_STATE_CHANGED`: `Ambient light changed: off -> 65%`
- `CAMERA_NODE_DISCONNECTED`: `Camera node disconnected`
- `CAMERA_NODE_CONNECTED`: `Camera node connected`
- `OTA_STATE_CHANGED`: `OTA state changed: idle -> downloading`
- `DEVICE_HEALTH_CHANGED`: `Device health changed: online -> degraded`
- `WIFI_SIGNAL_DEGRADED`: `Wi-Fi signal degraded: -58 -> -82 dBm`
- `WIFI_SIGNAL_RECOVERED`: `Wi-Fi signal recovered: -82 -> -60 dBm`
- `PROVISIONING_STARTED`: `Provisioning started`
- `PROVISIONING_SUCCESS`: `Provisioning completed`
- `PROVISIONING_FAILED`: `Provisioning failed: claim token expired`
- `IMAGE_CAPTURE_STARTED`: `Image capture started`
- `IMAGE_CAPTURED`: `Image captured #91`
- `IMAGE_UPLOAD_STARTED`: `Image upload started`
- `IMAGE_UPLOADED`: `Image uploaded #91 (manual)`
- `IMAGE_UPLOAD_FAILED`: `Image upload failed: camera timeout`
- `COMMAND_POLL_STALE`: `Command polling stale for 305s`

Unknown event types fall back to a safe humanized label.

## State Changes

The backend derives state-change events during heartbeat, diagnostics,
command-result, OTA status, setup status, and image ingestion. It compares the
incoming payload with the latest known canonical event for the same hardware
node when state comparison is needed, then writes a separate concise event when
a meaningful transition happens.

Current thresholds and dedupe behavior:

- Wi-Fi degraded: RSSI crosses to `<= -80 dBm`.
- Wi-Fi recovered: after degradation, RSSI reaches `>= -70 dBm`.
- OTA progress-only updates do not emit `OTA_STATE_CHANGED`.
- Repeated identical actuator and health states do not emit duplicate state
  events.
- Command polling stale emits once when heartbeat runtime crosses
  `command_poll_stale_seconds >= 300`.
- Provisioning events are deduplicated per provisioning phase and primary node.
- Image capture/upload events are deduplicated by command or image message
  correlation id.

## UI

The web dashboard includes a diagnostics timeline panel with:

- newest-first event rows
- event, severity, node, correlation, and text filters
- severity markers
- expandable JSON details
- load-more pagination

Expanded details include the compact event data, correlation id, hardware id,
node role, code, and message when present.

## Timestamp Behavior

Timeline row ordering uses backend canonical `occurred_at` timestamps. Firmware
contract `sent_at` values remain available in expanded details when present and
are useful for command, OTA, and heartbeat causality debugging. Firmware sends an
epoch fallback before NTP sync, then real UTC timestamps after SNTP succeeds.

## Current Limitations

- Event grouping is not implemented yet. OTA progress events may appear as
  individual rows.
- Large JSON payloads are compacted by the API rather than fetched lazily.
- Offline detection events depend on the existing backend detection logic.
- State comparison currently uses recent canonical event data instead of a
  dedicated state snapshot table.
