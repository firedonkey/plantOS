# PlantLab Raspberry Pi SoftAP Provisioning

For the full Raspberry Pi run-command list, use:

- [COMMANDS.md](/Users/gary/plantOS/device/raspberry_pi/COMMANDS.md)

This service implements the Raspberry Pi side of the SoftAP provisioning flow described in `provision_readme.md`.

## File Structure

```text
device/
  raspberry_pi/
    provision.py
    provisioning/
      __init__.py
      backend.py
      device_identity.py
      network.py
      service.py
      state.py
      storage.py
      web.py
      wifi.py
```

## Run On Raspberry Pi

From the Raspberry Pi device folder:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provision.py --backend-url https://marspotatolab.com
```

By default, network commands run in dry-run mode. This lets you test the setup page and backend registration code without changing the Pi network stack.

Open the setup page:

```text
http://<pi-ip>:8080
```

For the real SoftAP flow, the target local address is:

```text
http://192.168.4.1
```

For the current Raspberry Pi OS image, real mode uses NetworkManager/nmcli.
NetworkManager hotspot mode usually serves the setup page at:

```text
http://10.42.0.1:8080
```

Run real mode only when you have Ethernet access to the Pi:

```bash
python provision.py \
  --backend-url https://plantlab-provision-api-418533861080.us-central1.run.app \
  --host 0.0.0.0 \
  --port 8080 \
  --real-network \
  --open-hotspot \
  --reset
```

## Local Config File

Provisioning state is stored at:

```text
data/provisioning/device_config.json
```

The file is written with `0600` permissions.

## Local Full-Stack Test

To bring up the full local test stack on your laptop with one command:

```bash
cd ~/plantOS
cp .env.local.example .env.local
docker compose --env-file .env.local -f docker-compose.local.yml up --build
```

This starts:

- PostgreSQL on `localhost:5432`
- PlantLab platform on `http://127.0.0.1:8000`
- Provisioning backend on `http://127.0.0.1:3000`

Both web services use the same PostgreSQL database, so a newly provisioned device will appear on the local platform webpage immediately.

## State Machine

The service uses these states:

- `factory_reset`
- `ap_mode`
- `credentials_received`
- `wifi_connecting`
- `backend_registering`
- `online`
- `error`

## Production Hardening TODOs

- Add a fallback SoftAP implementation for non-NetworkManager Pi images.
- Add recovery behavior that re-enters AP mode after Wi-Fi or backend registration failure.
- Encrypt or otherwise protect stored Wi-Fi credentials.
- Remove the claim token after both success and unrecoverable failure.
- Add retry and backoff for backend registration.
- Add a device-local status endpoint so the setup page can show progress.
- Add a physical factory reset button handler.
- Add systemd service files for boot-time provisioning.

## Wi-Fi Layer Example

The Wi-Fi layer returns structured status objects instead of only logging:

```python
from provisioning.wifi import WiFiConnectionLayer

wifi = WiFiConnectionLayer(dry_run=True)
status = wifi.connect("HomeWiFi", "secret-password")
if not status.ok:
    print(status.stage, status.message)
```
