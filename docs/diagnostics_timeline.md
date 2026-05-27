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

Unknown event types fall back to a safe humanized label.

## UI

The web dashboard includes a diagnostics timeline panel with:

- newest-first event rows
- event, severity, node, correlation, and text filters
- severity markers
- expandable JSON details
- load-more pagination

Expanded details include the compact event data, correlation id, hardware id,
node role, code, and message when present.

## Current Limitations

- Event grouping is not implemented yet. OTA progress events may appear as
  individual rows.
- Large JSON payloads are compacted by the API rather than fetched lazily.
- Offline detection events depend on the existing backend detection logic.
