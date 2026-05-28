# OTA Protocol

OTA is a specialized command flow. The backend still serves firmware manifests
and artifacts through the existing OTA endpoints, while the contract layer adds
typed command parameters, typed status reports, compatibility checks, and
canonical events.

Lifecycle:

```text
idle -> available -> preparing -> downloading -> validating -> installing -> rebooting -> success
                                                                                 -> failed
                                                                                 -> rolled_back
```

OTA command params are used with `COMMAND` payloads whose `command_type` is
`START_OTA`:

```json
{
  "target_version": "1.2.0",
  "firmware_channel": "beta",
  "download_url": "https://...",
  "checksum_sha256": "abc123",
  "hardware_model": "plantlab-main-v2",
  "minimum_current_version": "1.1.0",
  "schema_major": 1
}
```

OTA status reports use the standard device message envelope with
`message_type: "OTA_STATUS"`:

```json
{
  "schema_version": "1.0",
  "message_id": "otamsg_01HX...",
  "hardware_device_id": "pl-esp32-64e0a80af6e8",
  "node_role": "master",
  "message_type": "OTA_STATUS",
  "sent_at": "2026-05-27T12:01:00Z",
  "payload": {
    "command_id": "cmd_01HX...",
    "status": "downloading",
    "progress_percent": 42,
    "current_version": "1.1.0",
    "target_version": "1.2.0",
    "firmware_channel": "beta",
    "phase": "download",
    "message": "Downloading firmware"
  }
}
```

Compatibility rules:

- The backend rejects unsupported schema major versions.
- `START_OTA` params can be checked against registered `hardware_model`.
- Minimum current firmware version is enforced before issuing a contract OTA
  command.
- Firmware releases may also set a maximum current firmware version.
- Firmware releases are channel-scoped. Devices poll `stable` unless they
  explicitly request another channel.
- Non-advancing target versions are rejected unless a future rollback command
  explicitly opts into rollback behavior.
- Existing legacy firmware may continue posting the old OTA status payload.

Staged rollout rules:

- Supported release channels are `dev`, `alpha`, `beta`, and `stable`.
  `local` remains available for local development contracts.
- `stable` manifest polling never receives `beta`, `alpha`, or `dev` releases.
- `rollout_percentage` uses a deterministic hash of release id and
  `hardware_device_id`, so a device stays in or out of a rollout consistently.
- `allowed_hardware_device_ids` bypasses the percentage gate for explicit
  device allowlists.
- Rollback metadata is stored on releases as `rollback_release_id` and
  `rollback_version`; firmware flashing behavior is unchanged.
- The admin diagnostics panel lists release channel, rollout percentage, and
  rollback version for quick support visibility.

Canonical events:

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

Firmware command execution:

- `START_OTA` commands are converted to an `OtaStartRequest` and handled by the
  existing OTA manager.
- Firmware requires `target_version` and `download_url`.
- Firmware accepts backend-owned artifact URLs only.
- Firmware reports `COMMAND_RESULT` `acked` immediately, then `in_progress`
  after the OTA manager accepts the request.
- Success is reported after reboot when the running firmware version matches
  the pending target version.
- Missing params, unsupported hardware, invalid checksum, or duplicate OTA
  starts are rejected cleanly.

Future work:

- Add admin UI controls for changing rollout percentage after publication.
- Add rollback artifact selection once firmware rollback policy is finalized.
