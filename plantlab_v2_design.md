# PlantLab v2 Updated System Design

## 1. Design Goal

PlantLab v2 upgrades the current Raspberry Pi based prototype into a lower-cost, modular ESP32-S3 based architecture.

The main goals are:

- Reduce device-side hardware cost
- Keep the system modular and expandable
- Support multiple camera viewpoints
- Avoid exposing camera-node setup to the user
- Keep the user-facing onboarding flow simple
- Keep the option to add a display, button, sensors, pump, and light control
- Keep AI and heavy image processing in the cloud

Housing redesign is intentionally postponed for now. This design focuses on electronics, device architecture, provisioning, and communication.

---

## 2. Final Architecture Direction

PlantLab v2 uses one master node and multiple hidden camera nodes.

```text
PlantLab Unit
├── Master Node: ESP32-S3 DevKitC
│   ├── Soil moisture sensor
│   ├── Temperature / humidity sensor
│   ├── Pump control
│   ├── LED / grow light control
│   ├── Provisioning button
│   ├── Optional display
│   └── Cloud connection
│
├── Camera Node 1: XIAO ESP32-S3 Sense
├── Camera Node 2: XIAO ESP32-S3 Sense
└── Camera Node 3: XIAO ESP32-S3 Sense
```

From the user’s view, there is only one device:

```text
My PlantLab
```

Internally, the cloud stores one PlantLab unit with several child nodes.

```text
User
└── PlantLab Unit
    ├── master node
    ├── camera node 1
    ├── camera node 2
    └── camera node 3
```

---

## 3. Selected Hardware

### 3.1 Master Node

Recommended master board:

```text
ESP32-S3-DevKitC-1-N32R16V
```

Reason:

- Official Espressif development board
- Good stability
- Enough GPIO for sensors, pump, light, button, and optional display
- High flash/PSRAM headroom for future expansion
- Good balance of cost and capability

Soil moisture for Phase 1 uses the ESP32-S3 internal ADC directly (no external ADC required).
This keeps bring-up simpler and reduces parts count.

---

### 3.2 Camera Nodes

Recommended camera-node board:

```text
Seeed Studio XIAO ESP32-S3 Sense
```

Reason:

- ESP32-S3 based
- Built-in camera
- Built-in Wi-Fi / BLE
- Small size
- Good for multi-camera placement
- No camera wiring required
- Good fit for a single-purpose camera node

Camera nodes will only handle camera-related tasks:

- Receive provisioning information from the master
- Connect to home Wi-Fi
- Register as hidden child devices in the cloud
- Capture images
- Upload images directly to the cloud
- Report status / heartbeat

The limited GPIO on the XIAO Sense is acceptable because camera nodes are not used for sensors, display, pump, or light control.

---

## 4. Communication Design

PlantLab v2 uses different communication methods for different jobs.

```text
Provisioning / local control:
Master Node <---- ESP-NOW ----> Camera Nodes

Normal cloud communication:
Master Node ---- Wi-Fi ----> Cloud
Camera Nodes ---- Wi-Fi ----> Cloud

Image upload:
Camera Nodes ---- HTTP upload ----> Cloud
```

Important rule:

```text
Images should not pass through the master node.
```

Camera nodes upload images directly to the cloud. The master only coordinates provisioning and control.

---

## 5. ESP-NOW Role

ESP-NOW is used for local ESP32-to-ESP32 communication without requiring the camera nodes to already know the home Wi-Fi credentials.

Use ESP-NOW for:

- Camera-node discovery
- Sending Wi-Fi credentials from master to camera nodes
- Sending unit ID / pairing token
- Assigning camera role or position
- Sending small local commands
- Heartbeat / status messages

Do not use ESP-NOW for:

- Image transfer
- Video streaming
- Large logs
- Firmware update packages

ESP-NOW is ideal here because it allows the master to automatically provision hidden camera nodes without user interaction.

---

## 6. Provisioning Flow

### 6.1 User-Facing Flow

The user only provisions the master device.

```text
1. User powers on PlantLab
2. User holds the master provisioning button
3. Master enters SoftAP provisioning mode
4. User connects phone/laptop to PlantLab setup Wi-Fi
5. User enters home Wi-Fi credentials
6. Master connects to home Wi-Fi
7. Master registers the PlantLab unit in the cloud
8. Master automatically provisions camera nodes
9. User sees one PlantLab device in the app/web platform
```

Camera provisioning is hidden from the user.

---

### 6.2 Internal Camera Provisioning Flow

```text
1. Camera nodes boot in unprovisioned mode
2. Camera nodes enable ESP-NOW and broadcast hello messages
3. Master receives hello messages and records camera node MAC addresses
4. Master sends provisioning package to each camera node using ESP-NOW
5. Camera nodes save Wi-Fi credentials and unit token
6. Camera nodes connect to home Wi-Fi
7. Camera nodes register with cloud as child devices
8. Cloud links camera nodes under the same PlantLab unit
```

Example provisioning package:

```json
{
  "type": "provision",
  "ssid": "HomeWiFi",
  "password": "wifi_password",
  "unit_id": "unit_123",
  "parent_device_id": "master_abc",
  "pairing_token": "short_lived_token",
  "role": "camera",
  "position": "front"
}
```

---

## 7. ESP-NOW Message Types

### 7.1 Camera Hello Message

Camera node broadcasts this when unprovisioned.

```json
{
  "type": "hello",
  "node_type": "camera",
  "device_id": "cam_temp_001",
  "firmware_version": "0.1.0"
}
```

### 7.2 Provision Message

Master sends this to each camera node.

```json
{
  "type": "provision",
  "ssid": "HomeWiFi",
  "password": "wifi_password",
  "unit_id": "unit_123",
  "parent_device_id": "master_abc",
  "pairing_token": "token_abc",
  "position": "front"
}
```

### 7.3 Provision ACK

Camera confirms provisioning data was received.

```json
{
  "type": "provision_ack",
  "device_id": "cam_001",
  "status": "received"
}
```

### 7.4 Wi-Fi Connected Status

Camera reports after joining Wi-Fi.

```json
{
  "type": "wifi_status",
  "device_id": "cam_001",
  "status": "connected",
  "ip": "192.168.1.51"
}
```

### 7.5 Capture Command

Master or cloud can trigger a camera capture.

```json
{
  "type": "capture",
  "request_id": "req_123",
  "reason": "scheduled_growth_check"
}
```

### 7.6 Heartbeat

Camera reports health.

```json
{
  "type": "heartbeat",
  "device_id": "cam_001",
  "battery_or_power": "external_5v",
  "wifi_rssi": -55,
  "uptime_sec": 3600
}
```

---

## 8. Wi-Fi and Cloud Communication

After provisioning, every node connects to home Wi-Fi.

### Master Node Sends

- Sensor readings
- Pump state
- Light state
- Device health
- Display / button status

Example endpoint:

```text
POST /api/devices/{device_id}/telemetry
```

Example payload:

```json
{
  "unit_id": "unit_123",
  "device_id": "master_abc",
  "soil_moisture": 52,
  "temperature_c": 23.5,
  "humidity_percent": 61,
  "light_state": "on",
  "pump_state": "off"
}
```

### Camera Node Sends

- Image uploads
- Capture status
- Heartbeat
- Error status

Example image endpoint:

```text
POST /api/devices/{device_id}/images
```

Image metadata example:

```json
{
  "unit_id": "unit_123",
  "device_id": "cam_001",
  "position": "front",
  "timestamp": "2026-04-25T22:00:00Z",
  "image_format": "jpeg"
}
```

---

## 9. Cloud Data Model

Recommended structure:

```text
users
└── user_id

plantlab_units
└── unit_id
    ├── owner_user_id
    ├── display_name
    ├── master_device_id
    └── created_at

devices
└── device_id
    ├── unit_id
    ├── role: master | camera
    ├── parent_device_id
    ├── position: front | side | top | unknown
    ├── firmware_version
    ├── last_seen_at
    └── status

sensor_readings
└── reading_id
    ├── unit_id
    ├── device_id
    ├── soil_moisture
    ├── temperature
    ├── humidity
    └── created_at

images
└── image_id
    ├── unit_id
    ├── device_id
    ├── position
    ├── storage_url
    ├── captured_at
    └── analysis_status
```

---

## 10. Hardware Connections

### 10.1 Master Node Connections

Master node connects to:

```text
I2C bus:
- Optional SHT31 temperature/humidity sensor
- Optional OLED display

ADC input:
- Soil moisture sensor direct to ESP32-S3 ADC1 GPIO (default GPIO1)

GPIO sensor input:
- DHT22 temperature/humidity sensor data pin

GPIO outputs:
- Pump MOSFET gate
- LED MOSFET gate
- Optional camera-node reset/enable lines

GPIO input:
- Provisioning button

Power:
- 5V main input
- 3.3V logic from board regulator
```

ADC safety and quality notes:

- ADC input must not exceed 3.3V.
- Use proper sensor/output scaling so the ADC pin always stays in valid range.
- ESP32 ADC readings can be noisy, so firmware should average multiple samples.
- Keep the firmware modular so an external ADC can be added later if accuracy becomes a problem.

### 10.2 Camera Node Connections

Each XIAO ESP32-S3 Sense camera node needs:

```text
5V power
GND
Optional reset/enable line from master
Optional debug UART header
```

No sensor or actuator connections are required on the camera nodes.

---

## 11. Power Architecture

Recommended power design:

```text
5V DC input
├── Master ESP32-S3 DevKitC
├── Camera Node 1
├── Camera Node 2
├── Camera Node 3
├── Pump power path
└── LED / grow light power path
```

Add protection and stability components:

- Fuse or polyfuse on main 5V input
- Bulk capacitor on 5V rail, for example 1000uF
- Smaller decoupling capacitors near modules
- Flyback diode or TVS protection for pump motor
- MOSFET switching for pump and LED
- Separate high-current traces for pump and LED loads

The master should not power the pump directly from a GPIO. GPIO only controls the MOSFET gate.

---

## 12. Recommended BOM Direction

### Core Boards

| Function | Recommended Part | Quantity |
|---|---|---:|
| Master node | ESP32-S3-DevKitC-1-N32R16V | 1 |
| Camera node | Seeed Studio XIAO ESP32-S3 Sense | 1 to 3 |

### Sensors and UI

| Function | Recommended Part | Quantity |
|---|---|---:|
| Temperature/humidity (default) | DHT22 | 1 |
| Temperature/humidity (optional upgrade) | SHT31 I2C sensor | 1 |
| Soil moisture | Capacitive soil moisture sensor | 1 |
| Display | 0.96 inch I2C OLED, optional | 1 |
| Provisioning input | Momentary push button | 1 |

Note:

- No ADS1115 is required for Phase 1.
- Keep I2C bus available for optional digital I2C sensors (for example SHT31) and optional OLED only.
- External ADC can be added in a later revision if internal ADC accuracy is insufficient.

### Power and Actuator Control

| Function | Recommended Part | Quantity |
|---|---|---:|
| Pump switch | AO3400A or similar logic-level N-MOSFET | 1 |
| LED switch | AO3400A or similar logic-level N-MOSFET | 1 |
| Pump protection | Schottky diode / flyback diode / TVS | 1 |
| Main input protection | Fuse or polyfuse | 1 |
| Bulk capacitor | 1000uF electrolytic | 1 to 2 |
| Power supply | 5V supply sized for master + cameras + pump + light | 1 |

---

## 13. Cost Direction

Approximate prototype cost:

```text
Master ESP32-S3 DevKitC:        $15
3x XIAO ESP32-S3 Sense:         $42 to $60
Sensors + display:              $15 to $30
MOSFETs + passives:             $5 to $10
Power supply + connectors:      $20 to $40
```

Estimated total:

```text
$100 to $155 prototype cost
```

Compared with Raspberry Pi 3 + 3 USB cameras, the ESP32 architecture should be:

- More modular
- Lower power
- Easier to scale into a product
- Better aligned with IoT architecture
- Slightly more complex in firmware because it has multiple nodes

---

## 14. Firmware Responsibilities

### 14.1 Master Firmware

Master firmware should support:

- Sensor reading (including soil moisture through internal ADC on GPIO1)
- Temperature/humidity reading (default DHT22; optional SHT31)
- Pump and LED control
- Optional display UI
- Button handling
- Local debug output and diagnostics

Master firmware should be implemented in phased scope:

- Phase 1: local hardware only (no Wi-Fi, no cloud, no provisioning, no ESP-NOW)
- Phase 2: cloud communication
- Phase 3: provisioning and onboarding flows

### 14.2 Camera Node Firmware

Camera firmware should support:

- Capture JPEG image
- Local camera bring-up and debug capture in Phase 1

Cloud upload and provisioning behavior is added in later phases.

---

## 15. Failure Handling

Recommended failure behavior:

### Camera cannot receive provisioning

- Keep broadcasting ESP-NOW hello
- Blink status LED if available
- Stay in unprovisioned mode

### Camera cannot connect to Wi-Fi

- Retry several times
- Notify master through ESP-NOW if possible
- Fall back to unprovisioned mode after repeated failure

### Camera cannot register with cloud

- Keep Wi-Fi connection
- Retry cloud registration
- Report status to master if possible

### Master cannot find camera nodes

- Continue normal operation with sensors and actuators
- Show warning on display / app
- Allow user to retry camera pairing

### Image upload fails

- Retry upload
- Optionally store latest image temporarily
- Do not block camera operation forever

---

## 16. Development Plan

### Phase 1: Hardware Bring-Up (Local Only)

Goal: prove local hardware behavior without network dependencies.

Must support:

- Read soil moisture sensor via ESP32-S3 internal ADC (default GPIO1)
- Read temperature/humidity sensor (DHT22 for current prototype)
- Capture image
- Control grow light MOSFET
- Control water pump MOSFET
- Keep pin definitions centralized in `config.h`

Do not include:

- Wi-Fi
- Cloud communication
- Provisioning
- ESP-NOW
- User account / device registration

Phase 1 `config.h` pin map plan:

```c
#define PIN_SOIL_MOISTURE_ADC 1

// Keep these only when optional SHT31 or OLED is present:
#define PIN_I2C_SDA 8
#define PIN_I2C_SCL 9
```

Remove from Phase 1 `config.h`:

```c
#define ADS1115_I2C_ADDR
#define ADS1115_CHANNEL
```

`sensor_manager` behavior for Phase 1:

- Read moisture with `analogRead(PIN_SOIL_MOISTURE_ADC)`
- Average at least 10 samples before reporting
- Print raw ADC value for bring-up diagnostics
- Optionally convert to percentage using dry/wet calibration constants in `config.h`
- Ensure ADC input never exceeds 3.3V

### Phase 2: Cloud Communication

Goal: connect working hardware to cloud with temporary test credentials.

Must support:

- Connect to Wi-Fi
- Send sensor data to cloud
- Upload captured image to cloud
- Receive cloud commands
- Control pump/light from command
- Report device health

Do not include yet:

- SoftAP provisioning
- User Wi-Fi setup flow
- ESP-NOW camera-node provisioning

### Phase 3: Provisioning and Product Onboarding

Goal: user-friendly setup for production behavior.

Must support:

- SoftAP provisioning
- User enters Wi-Fi credentials
- Save credentials in flash/NVS
- Device registers itself to cloud
- Later add ESP-NOW camera-node provisioning for hidden camera nodes

---

## 17. Open Questions

These should be decided later:

- Final camera position names: front, side, top, close-up?
- Whether camera nodes need local image buffering
- Whether master should control camera-node power/reset lines
- Whether external antenna is needed
- Whether XIAO camera quality is enough for plant analysis
- Whether to add OTA firmware update for master and camera nodes
- Whether to add local MQTT or cloud-only command flow

---

## 18. Current Recommendation

For the next prototype build, use:

```text
Master:
- ESP32-S3-DevKitC-1-N32R16V

Camera nodes:
- Seeed Studio XIAO ESP32-S3 Sense x 1 first
- Expand to x 3 after one camera node works

Communication:
- ESP-NOW for master-to-camera provisioning and small control messages
- Wi-Fi for cloud connection
- HTTP for image upload

User experience:
- User provisions only the master device
- Camera nodes are hidden child devices
```

This keeps the system low cost, modular, and easy to prototype while preserving a clear path to a more product-ready design later.
