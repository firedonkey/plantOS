# AI Plant Lab Kit

A Raspberry Pi 3 based indoor plant monitoring and control MVP for hobbyists, makers, and educators.

## Overview

This project is an early developer / prosumer kit for a closed-loop plant intelligence system.

The MVP can:
- read soil moisture
- read temperature and humidity
- control a small water pump
- control a USB grow light
- capture plant images from a USB webcam
- log data locally
- provide a simple local web dashboard

Longer term, this project may expand into a polished smart planter product and then into broader outdoor or yard automation.

## Product idea

This is not just a smart planter.

The core loop is:
- Observe
- Decide
- Act
- Learn

For the MVP, the emphasis is reliability, simplicity, and fast iteration.

## Hardware

### Already available
- Raspberry Pi 3
- breadboard
- jumper wires
- USB webcam (Logitech C270)
- DHT22 temperature and humidity sensor module
- 5V relay module
- 5V mini submersible water pump
- USB LED strip / grow light

### Ordered / arriving
- capacitive soil moisture sensor
- ADC module for analog sensor input
- SD card

## System architecture

### Inputs
- USB camera
- soil moisture sensor
- DHT22 sensor

### Outputs
- water pump via relay
- USB light via relay

### Controller
- Raspberry Pi 3

## Software goals

The software should include:
- sensor reading modules
- actuator control modules
- image capture
- periodic automation logic
- local logging
- a simple Flask dashboard

## Repository structure

```text
plantOS/
  README.md
  readme_PRD.md
  docs/
    api_contract.md
  device/
    requirements.txt
    requirements-pi.txt
    config.yaml
    app.py
    main.py
    sensors/
    actuators/
    camera/
    services/
    dashboard/
    data/
      logs/
      images/
  platform/
    requirements.txt
    app/
      main.py
      api/
      core/
      db/
      models/
      schemas/
      services/
      web/
    tests/
```

The `device/` app runs on the Raspberry Pi and owns hardware-level debugging. The `platform/` app runs the FastAPI web platform. The two apps communicate over HTTP and should not import each other.

## MVP behavior

### Watering
- read soil moisture periodically
- if moisture drops below a threshold, turn on the pump for a short duration
- log the event

### Lighting
- run the USB grow light on a daily schedule
- allow manual override later

### Camera
- capture still images periodically
- save timestamped images locally
- support future timelapse generation

### Logging
- store:
  - timestamp
  - temperature
  - humidity
  - moisture value
  - light state
  - pump events
  - image path

## Raspberry Pi 3 notes

- use Raspberry Pi OS Lite (32-bit)
- power via micro-USB with a stable 5V 2.5A or higher supply
- do not power the pump directly from the Pi
- USB light should also use external power through relay switching
- moisture sensor requires an ADC because the Pi has no analog input
- relay boards may be active-low, so software should support configurable active state

## Setup plan

### 1. Flash OS
Use Raspberry Pi Imager and select:
- Raspberry Pi OS Lite (32-bit)

Before writing the SD card, set:
- hostname
- username and password
- Wi-Fi credentials
- enable SSH

### 2. Boot Pi
- insert SD card
- connect power
- wait for boot
- SSH in from laptop

### 3. Install base packages
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

### 4. Create project environment
```bash
mkdir -p ~/projects/plant-ai-kit
cd ~/projects/plant-ai-kit
python3 -m venv .venv
source .venv/bin/activate
```

### 5. Install Python dependencies
For device laptop/mock-mode development:
```bash
cd device
pip install -r requirements.txt
```

For Raspberry Pi hardware access:
```bash
cd device
pip install -r requirements-pi.txt
```

For platform development:
```bash
cd platform
pip install -r requirements.txt
```

Optional camera helpers on Raspberry Pi OS:
```bash
sudo apt install fswebcam
sudo apt install python3-opencv
```

DHT22 support uses the CircuitPython DHT library. On Raspberry Pi OS, install the system GPIO helper first:

```bash
sudo apt install libgpiod2
```

## Test flow

### Laptop mock test
Keep `hardware.mock_mode: true` in `device/config.yaml`, then run:
```bash
cd device
python main.py --once
python -m flask --app app run --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000`.

To test a real USB webcam while the rest of the device stays in mock mode, keep:

```yaml
hardware:
  mock_mode: true

camera:
  enabled: true
  mock_mode: false
  device_index: 0
  resolution: 1280x720
  skip_frames: 30
```

Then run one cycle and refresh the local device dashboard:

```bash
cd device
python main.py --once
python -m flask --app app run --host 0.0.0.0 --port 5000
```

For a webcam stress test, run the automation loop with a short loop interval and capture interval:

```bash
cd device
python main.py --loop-interval 2 --capture-interval 2
```

This asks the app to wake up every 2 seconds and capture a webcam image every 2 seconds. Stop with `Ctrl+C`.

To test a real DHT22 while the rest of the device stays in mock mode, keep global mock mode on but set the DHT22 override off:

```yaml
hardware:
  mock_mode: true

sensors:
  dht22:
    enabled: true
    mock_mode: false
    gpio_pin: 4
    retries: 5
    retry_delay_seconds: 2
```

`gpio_pin: 4` means BCM GPIO 4, physical pin 7 on the Raspberry Pi header.

Then install Pi requirements and run one cycle:

```bash
pip install -r requirements-pi.txt
python main.py --once
```

### Send Raspberry Pi data to the platform
Start the platform first. Use `0.0.0.0` when another device, such as the Raspberry Pi, needs to connect:

```bash
cd platform
source ../.venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Sign in, add a device, then open that device dashboard and copy:

- `Device ID`
- `X-Device-Token`

On the Raspberry Pi, send real device readings and real captured camera images:

```bash
cd device
source ../.venv/bin/activate
python platform_client.py --platform-url http://your-laptop-ip:8000 --device-id 1 --device-token paste-token-here --interval 10 --image-every 1
```

The platform client also polls for pending pump/light commands every cycle, executes them locally, acknowledges the result back to the platform, and sends an immediate status update after commands. Use `--skip-commands` to send data without polling commands. Manual light commands pause the normal light schedule for `actuators.light.manual_override_seconds`.

When the Pi has a real camera enabled, uploaded images come from the latest camera capture path returned by the automation cycle. For frequent real image uploads, set `camera.capture_interval_seconds` low enough to match the sender cadence.

You can also save the values under `platform:` in `device/config.yaml` and run:

```bash
python platform_client.py
```

### Send mock data to the platform
Use the mock sender when you want to exercise the platform without waiting on real hardware:

```bash
cd device
source ../.venv/bin/activate
python mock_platform_sender.py --device-id 1 --device-token paste-token-here --once
```

To send mock readings every 5 seconds and upload one bundled mock rose image every 3 cycles:

```bash
python mock_platform_sender.py --device-id 1 --device-token paste-token-here --interval 5 --image-every 3
```

You can also save the values under `platform:` in `device/config.yaml` and run:

```bash
python mock_platform_sender.py
```

The mock sender forces mock mode for DHT22, moisture, and camera. It still polls pending pump/light commands and acknowledges them with mock actuators unless `--skip-commands` is used.

### Raspberry Pi mock test
Copy the repo to the Pi, keep `hardware.mock_mode: true`, then run:
```bash
cd device
python main.py --once
python -m flask --app app run --host 0.0.0.0 --port 5000
```

Open `http://<pi-ip-address>:5000` from another device on the same network.

### Raspberry Pi wired test
After wiring the sensors, relays, pump, light, and camera, set:
```yaml
hardware:
  mock_mode: false
```

Start with a short pump run time while testing:
```yaml
actuators:
  pump:
    run_seconds: 2
    cooldown_seconds: 3600
```

## Web dashboard and phone app path

The Flask dashboard is also a lightweight progressive web app.

Run it locally:
```bash
cd device
source .venv/bin/activate
python -m flask --app app run --host 127.0.0.1 --port 5000
```

Run it on the Pi for other devices on the network:
```bash
cd device
source .venv/bin/activate
python -m flask --app app run --host 0.0.0.0 --port 5000
```

On iPhone:
- open `http://<pi-hostname-or-ip>:5000` in Safari
- tap Share
- tap Add to Home Screen
- launch PlantOS from the Home Screen

The web app includes:
- mobile-friendly dashboard layout
- live status refresh
- app manifest
- service worker shell cache
- iPhone Home Screen metadata

## Platform app

Run the FastAPI platform locally:

```bash
cd platform
source ../.venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

Run platform tests:

```bash
cd platform
source ../.venv/bin/activate
python -m pytest tests
```

## Coding priorities

Build in this order:
1. project scaffold
2. DHT22 read
3. ADC moisture read
4. relay control
5. pump control
6. light control
7. camera capture
8. local logger
9. automation loop
10. Flask dashboard

## Safety / reliability rules

- default pump OFF on startup
- default light OFF on startup unless schedule says otherwise
- keep GPIO mapping in config file
- avoid hardcoding thresholds in multiple places
- log all pump activations
- keep code modular and easy to debug

## Non-goals for MVP

- advanced ML models
- disease classification with high accuracy
- dimming control
- cloud backend
- mobile app
- automatic fertilizer or medicine dispensing

## Success criteria

The MVP is successful if it can:
- read sensors reliably
- water automatically when dry
- turn the light on and off on schedule
- capture images over time
- show basic status in a local dashboard

## First task for Codex

Create the repository structure, `requirements.txt`, `config.yaml`, and Python stubs for:
- DHT22 reading
- ADC moisture reading
- relay control
- pump control
- light control
- camera capture
- logging
- main automation loop
- minimal Flask dashboard
