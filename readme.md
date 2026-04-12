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

## Proposed repository structure

```text
plant-ai-kit/
  README.md
  requirements.txt
  config.yaml
  app.py
  main.py
  sensors/
    dht22.py
    moisture_adc.py
  actuators/
    relay.py
    pump.py
    light.py
  camera/
    capture.py
  services/
    automation.py
    logger.py
    scheduler.py
  dashboard/
    templates/
    static/
  data/
    logs/
    images/
```

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
For laptop or mock-mode development:
```bash
pip install -r requirements.txt
```

For Raspberry Pi hardware access:
```bash
pip install -r requirements-pi.txt
```

Optional camera helpers on Raspberry Pi OS:
```bash
sudo apt install fswebcam
sudo apt install python3-opencv
```

## Test flow

### Laptop mock test
Keep `hardware.mock_mode: true` in `config.yaml`, then run:
```bash
python main.py --once
flask --app app run --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000`.

### Raspberry Pi mock test
Copy the repo to the Pi, keep `hardware.mock_mode: true`, then run:
```bash
python main.py --once
flask --app app run --host 0.0.0.0 --port 5000
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
