# PlantLab Raspberry Pi SoftAP Provisioning

This service implements the Raspberry Pi side of the SoftAP provisioning flow described in `provision_readme.md`.

## File Structure

```text
device/
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

From the device folder:

```bash
cd ~/projects/plantOS/device
source ../.venv/bin/activate
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

When real `hostapd`, `dnsmasq`, and `nmcli` setup is ready, run:

```bash
sudo ../.venv/bin/python provision.py \
  --backend-url https://marspotatolab.com \
  --host 0.0.0.0 \
  --port 80 \
  --real-network
```

## Local Config File

Provisioning state is stored at:

```text
data/provisioning/device_config.json
```

The file is written with `0600` permissions.

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

- Replace dry-run SoftAP commands with tested `hostapd` and `dnsmasq` configuration.
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
