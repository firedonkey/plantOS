# PlantLab Simulator

The PlantLab simulator is a lightweight developer tool for exercising backend
protocols, dashboards, OTA flow, command polling, and diagnostics timelines
without physical ESP32 hardware.

It uses the same hardware APIs as firmware:

- `POST /api/device-nodes/register`
- `POST /api/hardware/heartbeat`
- `POST /api/hardware/readings`
- `POST /api/hardware/diagnostics`
- `GET /api/hardware/commands/poll`
- `POST /api/hardware/commands/{id}/result`
- `POST /api/hardware/ota/status`
- `POST /api/image`
- `POST /api/hardware/image-upload/report`

It does not bypass the contract protocol layer.

## Quick Start

Start the local backend first, then run:

```bash
cd /Users/gary/plantOS
python3 tools/simulator/simulator.py \
  --base-url http://localhost:8000 \
  --device-id 1 \
  --device-token YOUR_REAL_DEVICE_API_TOKEN \
  --devices 1 \
  --camera-nodes 2 \
  --sensor-interval 10 \
  --image-interval 300
```

`YOUR_REAL_DEVICE_API_TOKEN` is the backend device `api_token`, not your web
login token and not the setup code. For local Docker, query the token with:

```bash
docker exec -it plantlab-local-postgres \
  psql -U plantlab_user -d plantlab \
  -c "select id, name, api_token from devices order by id;"
```

For local SQLite, one quick check is:

```bash
cd /Users/gary/plantOS/platform/backend
../../.venv/bin/python - <<'PY'
from app.db.session import SessionLocal
from app.models import Device

with SessionLocal() as session:
    for device in session.query(Device).order_by(Device.id):
        print(device.id, device.name, device.api_token)
PY
```

Useful environment variables:

```bash
export PLANTLAB_SIM_BASE_URL=http://localhost:8000
export PLANTLAB_DEVICE_ID=1
export PLANTLAB_DEVICE_TOKEN=YOUR_REAL_DEVICE_API_TOKEN
```

Then:

```bash
python3 tools/simulator/simulator.py --devices 1 --camera-nodes 2
```

If you see `diagnostics endpoint is unavailable` or `contract command polling
endpoint is unavailable`, your Docker backend image is older than the contract
protocol code. Rebuild it:

```bash
docker compose -f platform/infra/docker/docker-compose.local.yml up --build
```

The simulator will keep heartbeat simulation running against older backends, but
diagnostics timeline and contract-native command simulation need the rebuilt
backend. When the legacy command endpoint is still available, the simulator
falls back to `GET /api/hardware/commands/pending` for master-node commands so
web/mobile light and capture controls can still be exercised locally.

## Config File

Use the example fixture:

```bash
python3 tools/simulator/simulator.py \
  --config tools/simulator/fixtures/local_device.example.json
```

Config files may define multiple backend devices by listing `devices`, each with
its own `device_id` and `device_token`.

## CLI Options

Common options:

- `--base-url`: backend URL, default `http://localhost:8000`
- `--device-id`: backend device id
- `--device-token`: backend device `api_token`
- `--devices`: number of simulated master nodes for the same backend device
- `--camera-nodes`: camera nodes per simulated master; the first two default to `top` and `side`
- `--scenario`: scenario name, repeatable
- `--heartbeat-interval`: seconds between heartbeat envelopes
- `--sensor-interval`: seconds between fake sensor readings
- `--image-interval`: seconds between fake image uploads
- `--command-poll-interval`: seconds between command polls
- `--run-seconds` or `--duration-seconds`: stop automatically
- `--ota-failure-rate`: random OTA failure probability from `0.0` to `1.0`
- `--command-failure-rate`: random command failure probability from `0.0` to `1.0`
- `--log-level`: `debug`, `info`, or `warning`

Use `--scenario help` to print supported scenarios.

## Scenarios

Supported scenario names:

- `normal`: no failure injection.
- `unstable_wifi`: randomly skips some heartbeat, diagnostics, and poll cycles.
- `ota_failure`: fails OTA during validation with `checksum_mismatch`.
- `ota_checksum_failure`: explicit checksum-failure alias.
- `ota_download_failure`: fails OTA during download.
- `ota_install_failure`: fails OTA during install.
- `ota_timeout`: fails OTA with timeout.
- `ota_rollback`: reports a rolled-back OTA state during install.
- `camera_disconnect`: reports camera runtime as offline/degraded.
- `camera_flapping`: alternates camera node availability.
- `reboot_loop`: periodically resets uptime and increments reboot counters.
- `heartbeat_timeout`: suppresses heartbeat emissions.
- `slow_command_ack`: delays command acknowledgements.
- `command_failure`: fails all command executions after ACK.
- `low_memory`: reports low heap and critical diagnostics.
- `image_upload_failure`: skips image uploads and reports upload failures.

Example:

```bash
python3 tools/simulator/simulator.py \
  --device-id 1 \
  --device-token YOUR_REAL_DEVICE_API_TOKEN \
  --scenario unstable_wifi \
  --scenario ota_failure
```

## Simulated Commands

The simulator polls `GET /api/hardware/commands/poll` and handles:

- `SET_GROW_LIGHT_BRIGHTNESS`
- `CAPTURE_IMAGE`
- `REQUEST_DIAGNOSTICS`
- `START_OTA`
- `REBOOT`
- `UPDATE_CAPTURE_INTERVAL`
- `ENTER_PAIRING_MODE`
- `FACTORY_RESET`

Each command gets an immediate `COMMAND_RESULT` with `acked`, followed by
`completed`, `failed`, or `rejected`.

If the contract-native poll endpoint is not available in an older local backend,
master nodes fall back to `GET /api/hardware/commands/pending` so current web
and mobile controls can still be tested.

## Sensor Data And Images

Master nodes post believable fake sensor readings to `/api/hardware/readings`.
The values drift over time instead of staying flat:

- air temperature
- humidity
- water temperature
- moisture
- water level state
- light state and brightness

Camera nodes upload a generated PNG to `/api/image` at startup and then every
`--image-interval` seconds. The multipart request includes `camera_node_id`,
`camera_role`, and an `IMAGE_UPLOAD` contract envelope in the `metadata` form
field. With two camera nodes, the simulator assigns `top` to phase offset `0`
seconds and `side` to phase offset `30` seconds. `CAPTURE_IMAGE` commands also
upload a generated PNG when the backend image endpoint is available. The image
is generated locally with the Python standard library and uses the real
multipart upload path, so the web dashboard gallery should populate without
physical camera hardware.

Each generated image includes a visible capture counter and small visual changes
so repeated captures are easy to distinguish.

The `image_upload_failure` scenario skips the binary upload and posts an
`IMAGE_UPLOAD` failure envelope to `/api/hardware/image-upload/report`, which
should appear in the diagnostics timeline as `IMAGE_UPLOAD_FAILED`.

## OTA Flow

`START_OTA` emits real `OTA_STATUS` envelopes:

1. `preparing`
2. `downloading`
3. `validating`
4. `installing`
5. `rebooting`
6. `success`

Failure scenarios emit `failed` or `rolled_back` with `failure_reason`.

`START_OTA` validates required params before running:

- `target_version`
- `download_url`
- optional `hardware_model`, which must match the simulated node when present

Invalid or duplicate OTA commands are reported as rejected.

## Diagnostics Timeline

Because simulator traffic uses the real hardware APIs, the dashboard timeline
should show realistic entries:

- heartbeat events
- diagnostics events
- command queued/sent/acked/completed/failed events
- OTA progress events
- image capture, image upload, and image upload failure events
- provisioning lifecycle events when setup status is queried
- degraded states from failure scenarios
- state-change events such as `ACTUATOR_STATE_CHANGED`,
  `WIFI_SIGNAL_DEGRADED`, `WIFI_SIGNAL_RECOVERED`,
  `CAMERA_NODE_DISCONNECTED`, `CAMERA_NODE_CONNECTED`, and
  `OTA_STATE_CHANGED`

Validation flow:

1. Start Docker backend/web.
2. Query the device token from Postgres.
3. Start the simulator.
4. Open `http://localhost:5173/devices/1`.
5. Toggle Grow LED or capture an image.
6. Open the diagnostics timeline and confirm heartbeat, command, diagnostics,
   OTA, or failure events appear.

Useful simulator scenarios for state-change validation:

- `unstable_wifi`: validates Wi-Fi degraded/recovered transitions when RSSI
  crosses the backend thresholds.
- `camera_disconnect` or `camera_flapping`: validates camera node
  disconnected/connected transitions.
- `ota_failure` or `ota_checksum_failure`: validates OTA state-change and
  failure timeline rows.
- Grow LED commands validate actuator state changes when the simulator reports
  the new light state.

For command and OTA timeline validation, use a rebuilt backend that includes
the contract-native endpoints. Older local backends still support basic
heartbeat, sensor, image, and legacy light command testing.

## Troubleshooting

Missing token:

```text
--device-token or PLANTLAB_DEVICE_TOKEN is required.
```

Use the Postgres token query above.

Placeholder token:

```text
The simulator needs a real device API token.
```

Replace the placeholder with the backend `devices.api_token` value.

401 unauthorized:

- Confirm the token is `api_token`, not a web auth token.
- Confirm `--device-id` matches the row that owns the token.
- Re-query local Docker Postgres:

```bash
docker exec -it plantlab-local-postgres \
  psql -U plantlab_user -d plantlab \
  -c "select id, name, api_token from devices order by id;"
```

Backend unavailable:

```bash
cd /Users/gary/plantOS
docker compose -f platform/infra/docker/docker-compose.local.yml up --build
```

Missing contract endpoints:

If you see warnings for `/api/hardware/diagnostics` or
`/api/hardware/commands/poll`, your running backend image is older than the
current source. Rebuild Docker. The simulator continues with supported older
paths where possible.

## Limitations

- The simulator does not emulate ESP-NOW radio behavior.
- CLI `--devices N` creates multiple simulated master nodes under the same
  backend device token. To simulate separate backend device records, use a JSON
  config with one token per device.
- Reliability is intentionally simple; there is no durable offline queue.

Future expansion ideas:

- scenario schedules loaded from JSON
- CI fixture that starts a local backend and validates timeline rows
- simulator mode for provisioning once that protocol is migrated
- optional fixtures that replay real sensor/image sequences
