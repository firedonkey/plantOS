# Contract Migration Plan

This is a staged migration, not a rewrite.

Stage 1, implemented now:

- Add shared contract folder and examples.
- Add Pydantic models for heartbeat and diagnostics envelopes.
- Keep legacy heartbeat and diagnostics payloads working.
- Add canonical event writer for heartbeat and diagnostics.
- Add TypeScript and firmware constants.

Stage 2, implemented now:

- Add command and command result contracts.
- Add backend Pydantic validation for command/result envelopes.
- Preserve legacy command APIs and firmware polling.
- Emit canonical command lifecycle events from the existing command table.

Stage 3, implemented now:

- Add OTA status and OTA command param contracts.
- Preserve legacy OTA manifest, artifact, and status behavior.
- Add OTA compatibility checks for schema major, hardware model, and minimum firmware version.
- Emit canonical OTA lifecycle events from existing OTA storage.

Stage 4, implemented now:

- Add contract-native command polling at `GET /api/hardware/commands/poll`.
- Return full typed `COMMAND` envelopes while preserving legacy polling.
- Mark returned commands as `sent` and emit `COMMAND_POLLED`/`COMMAND_SENT`.

Stage 5, implemented now:

- Add optional actuator and runtime state to heartbeat v1.
- Emit contract `HEARTBEAT` envelopes from master firmware when required
  envelope fields are available.
- Preserve legacy heartbeat payload fallback.

Stage 6, implemented now:

- Add the diagnostics timeline API on top of canonical events.
- Add a web diagnostics timeline panel for command, OTA, heartbeat, and runtime
  debugging.

Stage 7, implemented now:

- Migrate image upload metadata.
- Emit image capture/upload lifecycle events while preserving legacy multipart
  uploads.
- Accept upload failure reports at `POST /api/hardware/image-upload/report`.

Stage 8, implemented now:

- Emit provisioning lifecycle events from setup status without changing BLE
  provisioning payloads.
- Deduplicate provisioning and image lifecycle events by phase/correlation id.

Stage 9, implemented now:

- Add OTA release channels, rollout percentages, hardware allowlists, current
  firmware upper bounds, and rollback metadata.
- Keep legacy manifest polling stable by defaulting devices to the `stable`
  channel.

Future stages:

- Generate Python and TypeScript types from JSON Schema.
- Add firmware helpers to build envelopes without repeated string literals.
- Migrate provisioning messages to contract envelopes.

Operational rule:

Do not remove legacy parsing until deployed firmware versions using the old
payloads are no longer active.
