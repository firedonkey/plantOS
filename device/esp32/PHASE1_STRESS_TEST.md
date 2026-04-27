# PlantLab v2 Phase 1 Stress Test

This runbook is the pre-Phase-2 gate for ESP32 firmware.

## 1) Flash test firmware

Master node (DevKitC):

```bash
cd /Users/gary/plantOS/device/esp32
./scripts/flash_esp32.sh --test-espnow-master --port /dev/cu.usbmodem1301
```

Camera node (XIAO ESP32-S3 Sense):

```bash
cd /Users/gary/plantOS/device/esp32
./scripts/flash_esp32.sh --test-espnow-camera --port /dev/cu.usbmodem12201
```

Do not keep `pio device monitor` open while running the stress harness.  
The stress script needs direct serial-port access.

## 2) Run automated protocol stress test

```bash
cd /Users/gary/plantOS/device/esp32
source /Users/gary/plantOS/.venv/bin/activate
python scripts/phase1_stress_test.py \
  --master-port /dev/cu.usbmodem1301 \
  --camera-port /dev/cu.usbmodem12201 \
  --duration 1800 \
  --capture-interval 5 \
  --health-interval 3
```

Quick 5-minute smoke:

```bash
python scripts/phase1_stress_test.py \
  --master-port /dev/cu.usbmodem1301 \
  --camera-port /dev/cu.usbmodem12201 \
  --duration 300
```

## 3) Exit criteria (Phase 1 protocol gate)

- Capture ACK failures: `0`
- Health ACK failures: `0`
- Health reports received: `> 0`
- Camera capture logs: `> 0`
- Script summary ends with `[PASS]`

## 4) Manual checks (non-protocol)

Before Phase 2, also verify:

1. Sensor soak on master (`dht22` + moisture ADC) for at least 30 minutes
2. Pump/light local control test for repeated toggles
3. Touch button behavior (known unstable item; tune before final release)
4. Camera standalone capture test (`--test-camera`) with SD writes

