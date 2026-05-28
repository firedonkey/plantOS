# PlantLab Local-to-Cloud Validation Gates

This plan validates existing PlantLab behavior only. It must not add product
features during validation; fixes should be limited to test automation,
checklists, smoke tests, stress tests, and defects found by those tests.

Execution rule:

1. Run one gate at a time.
2. Do not move to the next gate unless the current gate passes.
3. If a gate fails, stop, document the failure, apply a focused safe fix, and
   rerun the failed gate.

## Gate 1: Local Simulator Stress

Goal: stress the local backend, database, contracts, timeline, and simulator.

Command:

```bash
cd /Users/gary/plantOS
RUN_SECONDS=15 scripts/stress/local_simulator_stress.sh
```

Useful shorter run while iterating:

```bash
cd /Users/gary/plantOS
SCENARIOS="normal unstable_wifi" DEVICE_COUNTS="1 5" RUN_SECONDS=10 \
  scripts/stress/local_simulator_stress.sh
```

Pass criteria:

- Backend tests pass.
- Simulator stress completes.
- Timeline API returns events.
- Local backend health remains OK.
- No critical backend errors in recent platform logs.
- Recent event count stays under the configured storm thresholds.
- Command lifecycle, OTA status lifecycle, and image events are visible.
- `git diff --check` passes.

## Gate 2: Local ESP32 OTA And Local Backend

Goal: verify one real ESP32 against the local backend.

Checklist:

- Build firmware:
  `./.venv/bin/pio run -d device/esp32 -e esp32-local`
- Flash one ESP32 if USB access is available.
- Connect/provision the ESP32 to the local backend.
- Confirm contract heartbeat and diagnostics arrive.
- Queue light and capture commands; confirm `COMMAND_RESULT` ack/completed.
- Publish a local OTA release with `platform/infra/scripts/ota_release.py`.
- Confirm manifest, `START_OTA`, `OTA_STATUS`, reboot, and version update.
- Confirm timeline shows the full flow and no reboot loop.

Pass criteria:

- Firmware build passes.
- ESP32 connects locally.
- OTA completes safely.
- Device returns after OTA with the target version.
- Timeline shows heartbeat, diagnostics, command, image, and OTA flow.

## Gate 3: GCP Simulator Stress

Goal: validate deployed backend/cloud infra before using real hardware.

Checklist:

- Confirm the intended backend/image migration has been deployed.
- Use a real GCP device id and api token.
- Run simulator scenarios against the GCP API: `normal`, `unstable_wifi`,
  `ota_failure`, `camera_disconnect`, and `command_failure`.
- Watch Cloud Run logs for 500s, auth failures, DB errors, and latency spikes.
- Check timeline loading and event volume.

Pass criteria:

- GCP backend remains stable.
- Simulator completes.
- Timeline works.
- No repeated 500s.
- No auth/token issues.
- No excessive event volume.

## Gate 4: Real ESP32 48-Hour GCP Soak

Goal: run one real ESP32 against GCP for 48 hours.

Checklist:

- Build GCP-target firmware config.
- Flash/provision ESP32 to GCP.
- Run for 48 hours.
- Monitor heartbeat continuity, free heap, RSSI, reconnects, image uploads,
  command polling, OTA status, reboot count, and timeline readability.
- Review Cloud Run logs for backend error storms.

Pass criteria:

- Device remains healthy for 48 hours.
- No memory leak symptoms.
- No repeated disconnect/reboot loop.
- No backend error storm.
- Timeline remains readable.
- OTA remains safe.

## Report Template

```text
Gate:
status: pass/fail/blocked
commands run:
results:
issues found:
fixes applied:
remaining risks:
safe to proceed to next gate: yes/no
```
