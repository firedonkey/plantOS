# PlantLab Raspberry Pi Command Guide

This is the master command list for the Raspberry Pi workflow.

Use this file as the main place to find run commands for:

- local laptop web stack
- Raspberry Pi provisioning
- Raspberry Pi data/image upload
- component tests
- troubleshooting helpers

## Conventions

Project root on Raspberry Pi:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
```

Project root on laptop:

```bash
cd ~/plantOS
```

## 1. Start Local Website Stack On Laptop

First time:

```bash
cd ~/plantOS
cp .env.local.example .env.local
docker compose --env-file .env.local -f docker-compose.local.yml up --build
```

Later restarts:

```bash
cd ~/plantOS
docker compose --env-file .env.local -f docker-compose.local.yml up
```

Run in background:

```bash
cd ~/plantOS
docker compose --env-file .env.local -f docker-compose.local.yml up -d
```

Stop the stack:

```bash
cd ~/plantOS
docker compose -f docker-compose.local.yml down
```

Stop and remove database volume too:

```bash
cd ~/plantOS
docker compose -f docker-compose.local.yml down -v
```

Local URLs:

- Platform UI: `http://127.0.0.1:8000`
- Provisioning backend: `http://127.0.0.1:3000`
- Backend health: `http://127.0.0.1:3000/health`


## 2. Raspberry Pi Config Files

Local stack config:

- [config.local.yaml](/Users/gary/plantOS/device/raspberry_pi/config.local.yaml)

GCP config:

- [config.gcp.yaml](/Users/gary/plantOS/device/raspberry_pi/config.gcp.yaml)

Open a config file on Pi:

```bash
cd ~/projects/plantOS/device/raspberry_pi
nano config.local.yaml
```

## 3. Start Provisioning On Raspberry Pi

### Local Stack Mode

Button-driven provisioning service:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provisioning/run_provisioning_service.py --config config.local.yaml
```

Direct SoftAP test:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provision.py --config config.local.yaml --real-network --open-hotspot --reset
```

### GCP Mode

Button-driven provisioning service:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provisioning/run_provisioning_service.py --config config.gcp.yaml
```

Direct SoftAP test:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provision.py --config config.gcp.yaml --real-network --open-hotspot --reset
```

## 4. Send Sensor Data And Images To PlantLab

These commands expect provisioning to already be complete and:

- `data/provisioning/device_config.json` to exist
- `platform_device_id` and `device_access_token` to be present

### Local Stack Mode

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python platform_client.py \
  --config config.local.yaml \
  --send-interval 10 \
  --command-interval 1 \
  --image-every 1
```

One-shot test:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python platform_client.py --config config.local.yaml --once --image-every 1
```

### GCP Mode

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python platform_client.py \
  --config config.gcp.yaml \
  --send-interval 10 \
  --command-interval 1 \
  --image-every 1
```

One-shot test:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python platform_client.py --config config.gcp.yaml --once --image-every 1
```

## 5. Production Boot Service

Systemd unit file in repo:

- [plantlab-device.service](/Users/gary/plantOS/device/raspberry_pi/systemd/plantlab-device.service)

Copy it into systemd on Raspberry Pi:

```bash
sudo cp ~/projects/plantOS/device/raspberry_pi/systemd/plantlab-device.service /etc/systemd/system/plantlab-device.service
```

Reload systemd:

```bash
sudo systemctl daemon-reload
```

Enable on boot:

```bash
sudo systemctl enable plantlab-device
```

Start now:

```bash
sudo systemctl start plantlab-device
```

Restart after code updates:

```bash
sudo systemctl restart plantlab-device
```

Check status:

```bash
sudo systemctl status plantlab-device
```

Follow logs:

```bash
sudo journalctl -u plantlab-device -f
```

## 6. Full Local Provisioning Flow

1. Start the local Docker stack on laptop.
2. On Raspberry Pi, start:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provisioning/run_provisioning_service.py --config config.local.yaml
```

3. Long press the device button for about 5 seconds.
4. Wait for the LED to blink and for `PlantLab-Setup` Wi-Fi to appear.
5. On laptop, open local platform and go through Add Device.
6. After SN verification, continue to local setup.
7. Connect laptop or phone to `PlantLab-Setup`.
8. Enter home Wi-Fi details.
9. After provisioning succeeds, start `platform_client.py`.

## 7. Button / LED / Provisioning Hardware Tests

### LED Test

Press space to toggle LED on GPIO24.

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provisioning/test_led_toggle.py
```

### Button Test

Print on button press/release on GPIO23.

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provisioning/test_button_press.py
```

### Provisioning State Test

Simulates short press, long press, and factory reset timing.

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python provisioning/test_provisioning.py
```

## 8. Button-Driven Production Flow

Production behavior after the systemd service is installed:

- On boot, the device service starts automatically.
- If the device is already provisioned, it automatically starts sending readings and images.
- If the user long-presses the button:
  - unprovisioned device: enter provisioning mode
  - already provisioned device: factory reset first, then enter provisioning mode
- After successful provisioning, data sending starts automatically.

## 9. Sensor / Actuator Component Tests

### Moisture ADC Test

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python test_adc.py
```

### Pump / Light GPIO Test

This toggles both GPIO17 and GPIO27 together with space or Enter.

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python test_gpio.py
```

### Pump Test

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python test_pump.py --config config.gcp.yaml
```

Use local config instead if needed:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python test_pump.py --config config.local.yaml
```

## 10. Automation Loop

Run one automation cycle:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python main.py --config config.gcp.yaml --once
```

Run continuously:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python main.py --config config.gcp.yaml
```

## 11. Mock Platform Sender

Local mock sender:

```bash
cd ~/projects/plantOS/device/raspberry_pi
source ../../.venv/bin/activate
python mock_platform_sender.py --config config.local.yaml --send-interval 10 --image-every 1
```

## 12. Wi-Fi Recovery Helpers On Raspberry Pi

Show saved connections:

```bash
nmcli connection show
```

Reconnect to home Wi-Fi:

```bash
sudo nmcli connection up MOTOD240
```

Test DNS / internet:

```bash
ping -c 3 github.com
```

## 13. Notes

- Do not run `provision.py` and `provisioning/run_provisioning_service.py` at the same time.
- Use `config.local.yaml` for laptop Docker testing.
- Use `config.gcp.yaml` for deployed-cloud testing.
- If `git pull` fails on Raspberry Pi, check Wi-Fi and DNS before assuming the repo is wrong.
