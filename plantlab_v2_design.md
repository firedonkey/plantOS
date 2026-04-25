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
ESP32-S3-DevKitC-1-N8R8
```

Reason:

- Official Espressif development board
- Good stability
- Enough GPIO for sensors, pump, light, button, and optional display
- 8MB flash + 8MB PSRAM
- Good balance of cost and capability

Optional upgrade:

```text
ESP32-S3-DevKitC-1U-N8R8
```

Use the `1U` version if an external antenna is desired for better range.

Avoid:

```text
ESP32-S3-DevKitC-1-N8
```

Reason: no PSRAM. The cost saving is small, but it reduces future flexibility.

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
- SHT31 temperature/humidity sensor
- Optional OLED display
- Optional ADC if needed

ADC input:
- Soil moisture sensor

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
| Master node | ESP32-S3-DevKitC-1-N8R8 | 1 |
| Camera node | Seeed Studio XIAO ESP32-S3 Sense | 1 to 3 |

### Sensors and UI

| Function | Recommended Part | Quantity |
|---|---|---:|
| Temperature/humidity | SHT31 I2C sensor | 1 |
| Soil moisture | Capacitive soil moisture sensor | 1 |
| Display | 0.96 inch I2C OLED, optional | 1 |
| Provisioning input | Momentary push button | 1 |

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

- SoftAP provisioning for user Wi-Fi setup
- Cloud registration
- ESP-NOW camera discovery
- ESP-NOW camera provisioning
- Sensor reading
- Pump and LED control
- Optional display UI
- Button handling
- Telemetry upload
- Command polling or MQTT subscription
- Health reporting

### 14.2 Camera Node Firmware

Camera firmware should support:

- Unprovisioned boot mode
- ESP-NOW hello broadcast
- Receive provisioning package from master
- Store Wi-Fi credentials and pairing token
- Connect to home Wi-Fi
- Register as child device in cloud
- Capture JPEG image
- Upload image to cloud
- Report heartbeat
- Retry failed uploads
- Factory reset / reprovisioning mode

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

### Phase 1: Master Only

- ESP32-S3 DevKitC reads sensors
- Controls pump and light
- Supports button
- Sends telemetry to cloud

### Phase 2: One Camera Node

- One XIAO ESP32-S3 Sense camera node
- ESP-NOW discovery
- Master sends Wi-Fi credentials
- Camera connects to Wi-Fi
- Camera registers as child device
- Camera uploads image to cloud

### Phase 3: Three Camera Nodes

- Add cam1, cam2, cam3
- Assign camera positions
- Add capture scheduling
- Add cloud grouping by PlantLab unit

### Phase 4: Product Refinement

- Improve PCB
- Improve enclosure
- Add display UI
- Improve onboarding flow
- Add better camera option if image quality is not enough

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
- ESP32-S3-DevKitC-1-N8R8

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
