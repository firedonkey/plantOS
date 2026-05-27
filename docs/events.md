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
- `DEVICE_ONLINE` when heartbeat reports `online`
- `COMMAND_QUEUED`
- `COMMAND_SENT`
- `COMMAND_POLLED`
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

The backend currently stores canonical events in the existing
`device_diagnostic_events` table to avoid a schema rewrite.

`HEARTBEAT_RECEIVED` event data contains the full contract heartbeat payload,
including optional actuator and runtime state when firmware reports it.

Timeline API:

- `GET /api/devices/{id}/timeline` returns newest-first canonical events for a
  device.
- Filters include event type, severity, node role, correlation id, and time
  windows.
- The backend returns concise summaries so clients can render a readable
  timeline without duplicating event interpretation logic.

TODO:

- Add `DEVICE_OFFLINE` when offline detection is centralized.
- Migrate provisioning and image events into this format.
- Decide whether analytics needs a separate append-only event table later.
