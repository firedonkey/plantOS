# Local ESP32 Validation

Use this checklist for Gate 2 of PlantLab local-to-cloud validation. This gate
requires one physical ESP32 when validating flash, OTA, reboot, image upload,
and live command behavior.

## Prerequisites

- Local Docker stack is running.
- Local backend is reachable at `http://localhost:8000`.
- A local device exists with an `api_token`.
- ESP32 can reach the laptop backend over Wi-Fi.

Get the local device token:

```bash
docker exec -it plantlab-local-postgres \
  psql -U plantlab_user -d plantlab \
  -c "select id, name, api_token from devices order by id;"
```

## Build

```bash
cd /Users/gary/plantOS
./.venv/bin/pio run -d device/esp32 -e esp32-local
```

## Manual Checklist

1. Flash one ESP32 with the `esp32-local` firmware environment.
2. Provision or configure it to use the local backend.
3. Confirm `/api/hardware/heartbeat` receives contract heartbeat envelopes.
4. Confirm `/api/hardware/diagnostics` receives diagnostics envelopes.
5. Queue a grow-light command from web or mobile.
6. Confirm command polling, ACK, and completed/failed `COMMAND_RESULT`.
7. Capture an image and confirm image upload plus image timeline events.
8. Publish a local OTA release.
9. Start OTA and confirm `OTA_STATUS` progresses through install/reboot.
10. Confirm device returns after OTA with the expected firmware version.
11. Confirm no reboot loop, no repeated backend 500s, and readable timeline.

## Smoke Check

After the ESP32 has been running locally, use:

```bash
DEVICE_ID=1 DEVICE_TOKEN=REAL_API_TOKEN_FROM_DB \
  scripts/stress/local_esp32_smoke_check.sh
```

Optional environment variables:

- `BASE_URL`, default `http://localhost:8000`
- `SINCE`, default `30m`
- `EXPECTED_HARDWARE_ID`
- `EXPECTED_VERSION`
- `MIN_HEARTBEATS`, default `1`

## Pass Criteria

- Firmware build passes.
- ESP32 connects locally.
- Contract heartbeat and diagnostics are visible.
- Commands produce lifecycle events and final results.
- Image capture/upload succeeds.
- OTA completes safely and device returns.
- Timeline shows heartbeat, diagnostics, command, image, and OTA flow.
- No reboot loop or backend error storm.

## Blocked Criteria

Gate 2 is blocked if no physical ESP32 is available for flash/OTA validation.
Do not proceed to Gate 3 until this gate is completed on real hardware.
