# Canonical Events

Canonical events provide one consistent event shape for diagnostics, support, and
future analytics.

Current event format:

```json
{
  "schema_version": "1.0",
  "event_type": "HEARTBEAT_RECEIVED",
  "severity": "info",
  "device_id": 33,
  "hardware_device_id": "pl-esp32-64e0a80af6e8",
  "node_role": "master",
  "occurred_at": "2026-05-27T12:00:00Z",
  "correlation_id": "evt_01HX...",
  "data": {}
}
```

Implemented writers:

- `HEARTBEAT_RECEIVED`
- `DIAGNOSTICS_RECEIVED`
- `DEVICE_ONLINE` when heartbeat transitions to `online`
- `DEVICE_OFFLINE` when heartbeat explicitly reports `offline`
- `ACTUATOR_STATE_CHANGED`
- `CAMERA_NODE_CONNECTED`
- `CAMERA_NODE_DISCONNECTED`
- `OTA_STATE_CHANGED`
- `DEVICE_HEALTH_CHANGED`
- `WIFI_SIGNAL_DEGRADED`
- `WIFI_SIGNAL_RECOVERED`
- `COMMAND_QUEUED`
- `COMMAND_SENT`
- `COMMAND_POLLED`
- `COMMAND_POLL_STALE`
- `COMMAND_IN_PROGRESS`
- `COMMAND_ACKED`
- `COMMAND_COMPLETED`
- `COMMAND_FAILED`
- `COMMAND_TIMED_OUT`
- `COMMAND_REJECTED`
- `OTA_AVAILABLE`
- `OTA_STARTED`
- `OTA_PREPARING`
- `OTA_DOWNLOADING`
- `OTA_VALIDATING`
- `OTA_INSTALLING`
- `OTA_REBOOTING`
- `OTA_SUCCESS`
- `OTA_FAILED`
- `OTA_ROLLED_BACK`
- `PROVISIONING_STARTED`
- `PROVISIONING_SUCCESS`
- `PROVISIONING_FAILED`
- `IMAGE_CAPTURE_STARTED`
- `IMAGE_CAPTURED`
- `IMAGE_UPLOAD_STARTED`
- `IMAGE_UPLOADED`
- `IMAGE_UPLOAD_FAILED`

The backend currently stores canonical events in the existing
`device_diagnostic_events` table to avoid a schema rewrite.

`HEARTBEAT_RECEIVED` event data contains the full contract heartbeat payload,
including optional actuator and runtime state when firmware reports it.

State-change events are derived by comparing a new payload with the previous
known canonical payload for that device node. The backend currently uses the
latest `HEARTBEAT_RECEIVED` and `DIAGNOSTICS_RECEIVED` events as the lightweight
snapshot source, so no new state table is required.

Deduplication rules:

- Ambient light changes emit only when `enabled` or `brightness_percent`
  changes.
- Camera node events emit only for `online -> offline` and `offline -> online`.
- OTA state changes emit only when status changes, not for progress-only
  updates.
- Wi-Fi signal degrades at `<= -80 dBm` and recovers at `>= -70 dBm`.
  The gap is intentional hysteresis to avoid flapping.
- Device health changes emit when heartbeat `node_status` or diagnostics
  status/severity changes.
- Command polling stale emits when heartbeat runtime reports
  `command_poll_stale_seconds >= 300` after previously being below the
  threshold. Repeated stale heartbeats do not emit duplicates.
- Provisioning lifecycle events are deduplicated per device/hardware node and
  provisioning phase.
- Image capture/upload lifecycle events are deduplicated by command or image
  message correlation id.

Timeline API:

- `GET /api/devices/{id}/timeline` returns newest-first canonical events for a
  device.
- Filters include event type, severity, node role, correlation id, and time
  windows.
- The backend returns concise summaries so clients can render a readable
  timeline without duplicating event interpretation logic.
- Image summaries include capture start, capture completion, upload start,
  successful uploads, image ids when available, upload reasons, and failure
  reasons.
- Provisioning summaries include started, completed, and failed states.

Timestamp behavior:

- Canonical event `occurred_at` is still backend-owned when hardware messages
  are received.
- Firmware envelope `sent_at` is used for causality debugging and correlation.
- Firmware sends `1970-01-01T00:00:00Z` before NTP sync and real UTC timestamps
  after sync.
- Backend validation tolerates a missing `sent_at` field for early boot
  compatibility.

TODO:

- Move snapshots into a dedicated state table only if event lookup becomes a
  measurable performance issue.
- Decide whether analytics needs a separate append-only event table later.
