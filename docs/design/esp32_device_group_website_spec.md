# ESP32 Device Group Website Spec

## Purpose

Define the website and platform behavior for an ESP32 PlantLab system where one user-visible device is made of multiple physical boards:

- one master node
- one or more camera nodes

This spec is intentionally website-first. It should guide platform, provisioning, and ESP32 implementation without breaking the existing Raspberry Pi path.

## Core Product Rule

One PlantLab device in the website is a **logical device group**.

That logical device group may contain:

- one Raspberry Pi board
- one ESP32 master node
- one ESP32 master node plus one or more camera nodes

From the user's perspective, these are all still just **one device**.

## Goals

- Keep the Raspberry Pi user flow working as it does today.
- Let the website understand one logical device with many hardware nodes.
- Keep one dashboard card and one device detail page per PlantLab device.
- Let the master node own commands, device state, and provisioning authority.
- Let camera nodes contribute images and node health without becoming separate user-visible devices.
- Allow future support for more than one camera node.

## Non-Goals

- Do not add a separate user-facing camera provisioning flow.
- Do not make camera nodes appear as standalone devices in the device list.
- Do not add a separate user-facing camera onboarding step.
- Do not change the Raspberry Pi path to require multi-node behavior.

## Terminology

### Logical device

The PlantLab device the user sees and manages in the website.

Owns:

- name
- location
- plant type
- readings timeline
- image gallery
- commands
- setup/removal lifecycle

### Hardware node

A physical board that belongs to a logical device.

Examples:

- Raspberry Pi board
- ESP32 master node
- ESP32 camera node 1
- ESP32 camera node 2

## Website Data Model

### Existing model to keep

Keep the current `Device` model as the top-level thing the user owns.

Relevant file:

- [device.py](/Users/gary/plantOS/platform/app/models/device.py)

### New model to add

Add a child concept: `DeviceNode`

Suggested fields:

- `id`
- `device_id`
- `hardware_device_id`
- `node_role`
  - `single_board`
  - `master`
  - `camera`
- `node_index`
  - nullable
  - useful for `Camera 1`, `Camera 2`
- `display_name`
  - `Raspberry Pi`
  - `Master`
  - `Camera 1`
- `hardware_model`
  - `raspberry_pi`
  - `esp32_master`
  - `xiao_esp32s3_camera`
- `hardware_version`
- `software_version`
- `capabilities` JSON
- `status`
  - `provisioning`
  - `online`
  - `offline`
  - `error`
- `last_seen_at`
- `created_at`
- `updated_at`

### Important ownership rule

- `Device` remains the user-facing object
- `DeviceNode` is internal structure the website can display

## Relationship to Existing Provisioning Tables

There is already a useful multi-hardware seam in the provisioning backend:

- [provisioning_schema.sql](/Users/gary/plantOS/provision_backend/src/db/provisioning_schema.sql)
- [deviceProvisioningService.js](/Users/gary/plantOS/provision_backend/src/services/deviceProvisioningService.js)

Current table:

- `device_hardware_ids`

This already supports:

- one logical platform device
- many hardware IDs attached to it

Recommended direction:

Extend that concept instead of inventing a second unrelated mapping.

Fields to add or derive there:

- `node_role`
- `node_index`
- optional `display_name`
- node-level `status`

## Device Behavior Rules

### Raspberry Pi

Treat Raspberry Pi as:

- one logical device
- one hardware node
- `node_role = single_board`

This keeps the current path valid with minimal change.

### ESP32 system

Treat ESP32 as:

- one logical device
- one master node
- zero or more camera nodes

The user still sees one device.

## Source of Truth Rules

### Master node owns

- command execution
- logical device state
- actuator state
- provisioning authority
- camera scheduling authority
- device-level readiness for onboarding

### Camera node owns

- image capture
- image upload
- camera-specific node heartbeat
- local camera health

### Logical device owns

- dashboard
- image gallery
- readings history
- commands
- remove/reset lifecycle

## Website Page Behavior

### Devices list page

Relevant file:

- [devices.html](/Users/gary/plantOS/platform/app/web/templates/devices.html)

Rule:

- show one card per logical device

Do not:

- show a separate card per camera node

Optional future metadata on the card:

- `Master online`
- `1 camera online`
- `1 camera needs setup`

### Device detail page

Relevant file:

- [device_detail.html](/Users/gary/plantOS/platform/app/web/templates/device_detail.html)

Keep the main sections:

- Sensor Readings
- Latest Capture
- Controls
- Recent Activity

Add a new section:

- `Device Components`

Example rows:

- `Master — online`
- `Camera 1 — online`
- `Camera 2 — awaiting provisioning`

Purpose:

- reveal multi-board state
- avoid turning the product into a multi-device UI

### Sensor Readings panel

Keep this device-level.

Source rules:

- soil moisture: master
- temperature: master
- humidity: master
- growing light: master
- pump: master
- last reading: latest master reading

Camera nodes must not overwrite device-level reading state.

### Camera panel

Keep this device-level.

Rules:

- latest image is latest image across attached camera nodes
- recent images is a combined gallery

Optional future enhancement:

- record and display image source label such as `Camera 1`

### Controls

Keep controls attached to the logical device.

Rules:

- user sends commands to logical device
- master node executes commands
- camera nodes do not receive direct user dashboard commands

## Setup and Onboarding Rules

### Shared user flow

From the user's perspective, provisioning stays:

1. Add device
2. Verify serial number
3. Join `PlantLab-Setup`
4. Enter Wi-Fi once
5. Finish setup

No separate camera onboarding page should exist.

### ESP32 onboarding semantics

For ESP32:

- user provisions only the master node
- master node provisions camera node(s) internally over ESP-NOW

Website outcome:

- create one logical device
- attach one master node first
- attach camera node(s) later

### Setup finishing rules

Relevant files:

- [routes.py](/Users/gary/plantOS/platform/app/web/routes.py)
- [setup_finishing.html](/Users/gary/plantOS/platform/app/web/templates/setup_finishing.html)

#### Raspberry Pi ready rule

Setup is ready when:

- logical device exists
- first reading exists
- first image exists

#### ESP32 ready rule

Setup is ready when:

- logical device exists
- master node exists
- first master reading exists

If camera capture is **not** expected for this setup, the flow may finish there.

If camera capture **is** expected for this setup, setup should also wait for:

- first image upload

Current desired behavior:

- master-only ESP32 setup may land after first reading
- master + camera ESP32 setup should land with the first image already present on the dashboard

## API and Backend Contract Rules

### Device summary endpoint

Current dashboard summary is device-level.

Recommended extension:

- keep device-level summary
- add `node_summary`

Suggested shape:

```json
{
  "device": {
    "id": 12,
    "name": "Device 1"
  },
  "latest_reading": {},
  "latest_image": {},
  "recent_images": [],
  "command_activity": [],
  "node_summary": {
    "master": {
      "status": "online",
      "last_seen": "2026-05-02T23:10:00Z"
    },
    "cameras": [
      {
        "label": "Camera 1",
        "status": "online",
        "last_seen": "2026-05-02T23:09:54Z"
      }
    ]
  }
}
```

### Node heartbeat

Current status endpoint:

- [status.py](/Users/gary/plantOS/platform/app/api/routes/status.py)

Problem:

- it is device-wide, not node-aware

Needed behavior:

- master heartbeat updates master node status
- camera heartbeat updates camera node status
- logical device status is derived from node state

Suggested device-level summary rule:

- if master is offline: device is degraded/offline
- if master is online and some cameras are offline: device is online with warning
- if all relevant nodes are online: device is healthy

### Sensor reading ingest

Current route:

- [readings.py](/Users/gary/plantOS/platform/app/api/routes/readings.py)

Rule:

- only nodes with reading capability may submit readings

Expected senders:

- Raspberry Pi single-board node
- ESP32 master node

Camera nodes should not send sensor readings.

### Image ingest

Current route:

- [images.py](/Users/gary/plantOS/platform/app/api/routes/images.py)

Rule:

- camera nodes may upload images to the logical device

Suggested future enhancement:

- store optional `source_node_id` on each image row

Gallery behavior remains device-level.

### Provisioned registration

Current provisioning registration:

- [provisioningSchemas.js](/Users/gary/plantOS/provision_backend/src/models/provisioningSchemas.js)
- [deviceProvisioningService.js](/Users/gary/plantOS/provision_backend/src/services/deviceProvisioningService.js)

Registration model should evolve to express:

- `hardware_device_id`
- `node_role`
- `node_index`
- `capabilities`
- whether registration is:
  - creating a new logical device group
  - attaching another node to an existing logical device

Expected cases:

- Raspberry Pi: create logical device + single node
- ESP32 master: create logical device + master node
- ESP32 camera: attach camera node to existing logical device

## Delete and Reset Rules

### Remove device

Relevant current service:

- [devices.py](/Users/gary/plantOS/platform/app/services/devices.py)

User action remains one button:

- `Remove device`

Behavior should mean:

- remove logical device
- revoke shared runtime identity
- remove attached node mappings
- release serial/provisioning associations

### Reprovision

For ESP32:

- long press on master starts reprovisioning for the whole group
- website still treats it as one device reprovisioning
- camera nodes should later rejoin through master

## Implementation Sequence

### Phase 1: website and platform data model

1. Add `DeviceNode` concept.
2. Extend provisioning-side hardware mapping with node metadata.
3. Keep current `Device` model as the user-facing object.

### Phase 2: website UX

1. Add node summary to device detail page.
2. Keep devices list one card per logical device.
3. Keep readings, controls, and gallery device-level.
4. Update setup-finishing rules so ESP32 setup behavior depends on whether camera capture is expected.

### Phase 3: platform APIs

1. Add node-aware heartbeat path.
2. Add node-aware registration/attach behavior.
3. Extend summary payload with node summary.
4. Optionally add image source-node metadata.

### Phase 4: master node implementation

1. Master provisions camera nodes over ESP-NOW.
2. Master owns image schedule and capture requests.
3. Master tracks paired/provisioned camera nodes.

### Phase 5: camera node implementation

1. Camera node receives provisioning info from master.
2. Camera node stores config locally.
3. Camera node sends node heartbeat.
4. Camera node uploads images as part of one logical device.

## Recommended First Code Changes

When implementation starts, do these first:

1. Add website/platform support for `DeviceNode`.
2. Add node-aware status/heartbeat model.
3. Extend provisioning registration to include node role.
4. Add node summary to dashboard payloads.

Only after that should we implement:

5. camera provisioning over ESP-NOW
6. camera node attach flow
7. master-driven capture scheduling

## Concrete Task List

This section breaks the spec into practical implementation tasks in the order we should tackle them.

### Stage 0: alignment and naming

- [ ] Confirm final naming for the new child concept:
  - `DeviceNode`
  - or reuse/expand provisioning-side `device_hardware_ids`
- [ ] Confirm final node-role enum values:
  - `single_board`
  - `master`
  - `camera`
- [ ] Confirm the product wording for the dashboard section:
  - `Device Components`
  - or `Hardware`

#### Stage 0 test plan

- [ ] Review the naming choices against both hardware families:
  - Raspberry Pi still reads naturally
  - ESP32 master + camera grouping reads naturally
- [ ] Confirm the chosen names are consistent across:
  - schema language
  - API language
  - UI language
- [ ] Pass criteria:
  - no ambiguous terms remain
  - we can describe Pi and ESP32 with the same model

### Stage 1: schema and persistence design

- [ ] Decide whether node metadata lives:
  - only in provisioning backend tables first
  - or also in the platform database
- [ ] Define the final node schema fields:
  - `device_id`
  - `hardware_device_id`
  - `node_role`
  - `node_index`
  - `display_name`
  - `hardware_model`
  - `hardware_version`
  - `software_version`
  - `capabilities`
  - `status`
  - `last_seen_at`
- [ ] Add the needed migration(s) for node metadata
- [ ] Add indexes needed for:
  - lookup by `device_id`
  - lookup by `hardware_device_id`
  - lookup by `node_role`

#### Stage 1 test plan

- [ ] Run migrations locally
- [ ] Verify schema objects exist in the database
- [ ] Insert sample rows for:
  - one Raspberry Pi node
  - one ESP32 master node
  - one ESP32 camera node
- [ ] Verify lookup performance basics:
  - query by logical device
  - query by hardware ID
- [ ] Pass criteria:
  - migrations apply cleanly
  - sample inserts succeed
  - no existing device data is broken

### Stage 2: platform model and service layer

- [ ] Add a platform-side model or query object for device nodes
- [ ] Add service helpers to:
  - list nodes for a logical device
  - upsert a node by `hardware_device_id`
  - update node heartbeat/status
  - mark node offline/stale later if needed
- [ ] Add a derived device-status helper that computes:
  - device healthy
  - device degraded
  - device offline
  from node state

#### Stage 2 test plan

- [ ] Add or run focused service/model tests for:
  - list nodes for device
  - upsert node by hardware ID
  - update node heartbeat
  - derive device status from node states
- [ ] Smoke test with:
  - Pi single-node device
  - ESP32 master-only device
  - ESP32 master + camera device
- [ ] Pass criteria:
  - service helpers return expected node sets
  - derived device status matches the intended rules
  - single-board Pi devices still behave correctly

### Stage 3: provisioning backend contract

- [ ] Extend registration payload schema in:
  - [provisioningSchemas.js](/Users/gary/plantOS/provision_backend/src/models/provisioningSchemas.js)
- [ ] Add fields for:
  - `node_role`
  - `node_index`
  - optional `display_name`
  - optional `attach_to_platform_device_id` or equivalent
- [ ] Update registration service in:
  - [deviceProvisioningService.js](/Users/gary/plantOS/provision_backend/src/services/deviceProvisioningService.js)
- [ ] Support three registration cases:
  - Raspberry Pi creates logical device + single node
  - ESP32 master creates logical device + master node
  - ESP32 camera attaches to existing logical device
- [ ] Preserve current Raspberry Pi registration behavior as the default path

#### Stage 3 test plan

- [ ] Add or run contract tests for registration payload validation
- [ ] Verify these registration cases:
  - Pi creates logical device + single node
  - ESP32 master creates logical device + master node
  - ESP32 camera attaches to existing logical device
- [ ] Verify invalid cases:
  - camera tries to attach to missing logical device
  - duplicate node registration with conflicting ownership
- [ ] Pass criteria:
  - all three intended registration cases succeed
  - Raspberry Pi registration still works unchanged
  - invalid cases fail with clear errors

### Stage 4: platform API changes

- [ ] Add a node-aware heartbeat endpoint
- [ ] Define request fields for node heartbeat:
  - logical `device_id`
  - `hardware_device_id`
  - `node_role`
  - status/message if needed
- [ ] Keep existing device-wide status endpoint working for Raspberry Pi during transition
- [ ] Add node-aware registration proxy support on platform if needed
- [ ] Extend device summary payload with `node_summary`

#### Stage 4 test plan

- [ ] Add or run API tests for:
  - node heartbeat endpoint
  - device summary with `node_summary`
  - backward compatibility of current device-wide status path
- [ ] Verify auth behavior for:
  - valid device token
  - invalid device token
  - wrong logical device
- [ ] Pass criteria:
  - node heartbeat updates only the intended node
  - summary payload includes correct node data
  - current Pi APIs still pass

### Stage 5: website summary and detail behavior

- [ ] Update device summary route to include node information
- [ ] Add `Device Components` section to:
  - [device_detail.html](/Users/gary/plantOS/platform/app/web/templates/device_detail.html)
- [ ] Show rows such as:
  - `Master — online`
  - `Camera 1 — online`
  - `Camera 2 — awaiting provisioning`
- [ ] Keep sensor cards driven by master data only
- [ ] Keep image gallery device-level
- [ ] Optionally show image source later, but do not require it for first rollout

#### Stage 5 test plan

- [ ] Rebuild local Docker
- [ ] Open a Pi device detail page and verify:
  - no broken layout
  - no duplicate node confusion
- [ ] Open an ESP32 device detail page and verify:
  - node summary renders cleanly
  - readings still look device-level
  - images still look device-level
- [ ] Verify empty and partial states:
  - no camera yet
  - camera offline
  - camera awaiting provisioning
- [ ] Pass criteria:
  - UI looks coherent for both Pi and ESP32
  - Pi dashboard remains simple
  - ESP32 dashboard shows components without looking like multiple devices

### Stage 6: devices list behavior

- [ ] Keep one card per logical device in:
  - [devices.html](/Users/gary/plantOS/platform/app/web/templates/devices.html)
- [ ] Add optional compact node-health text such as:
  - `Master online`
  - `1 camera online`
  - `1 camera needs setup`
- [ ] Do not expose camera nodes as independent cards

#### Stage 6 test plan

- [ ] Verify device list for:
  - Pi account with one device
  - ESP32 account with one master + one camera
  - mixed account with Pi and ESP32 devices
- [ ] Confirm one card per logical device only
- [ ] Verify optional compact node-health text, if added
- [ ] Pass criteria:
  - no camera node appears as its own device card
  - existing Pi cards still render correctly

### Stage 7: setup-finishing logic

- [ ] Update setup-finishing readiness logic in:
  - [routes.py](/Users/gary/plantOS/platform/app/web/routes.py)
- [ ] Keep Raspberry Pi ready rule:
  - device exists
  - first reading exists
  - first image exists
- [ ] Keep ESP32 master ready rule:
  - logical device exists
  - master node exists
  - first master reading exists
- [ ] Do not wait for:
  - camera node provisioning
  - first image upload
- [ ] Update setup-finishing UI copy so ESP32 users are not told to wait on a camera image

#### Stage 7 test plan

- [ ] Test Raspberry Pi onboarding locally:
  - setup page
  - finishing page
  - redirect after first image
- [ ] Test ESP32 master onboarding locally:
  - setup page
  - finishing page
  - redirect after master reading without waiting for image
- [ ] Verify malformed/legacy query handling still works
- [ ] Pass criteria:
  - Pi still waits for image
  - ESP32 no longer waits for image
  - both flows redirect correctly

### Stage 8: reading and image attribution

- [ ] Restrict sensor reading ingestion to:
  - Raspberry Pi node
  - ESP32 master node
- [ ] Prevent camera nodes from posting device-level sensor readings
- [ ] Extend image ingestion so camera uploads can carry optional node identity
- [ ] Decide whether `images` table needs:
  - `source_node_id`
  - or whether source can stay implicit for phase 1

#### Stage 8 test plan

- [ ] Verify master-origin readings are accepted
- [ ] Verify camera-origin readings are rejected
- [ ] Verify camera image upload succeeds for attached camera node
- [ ] If `source_node_id` is added, verify it is stored correctly
- [ ] Pass criteria:
  - device-level readings come only from valid reading nodes
  - camera uploads contribute to the device gallery correctly

### Stage 9: delete and reset semantics

- [ ] Update delete/remove behavior so removing one logical device also removes attached nodes
- [ ] Ensure serial/provisioning cleanup releases:
  - master node mapping
  - camera node mappings
- [ ] Define reprovisioning semantics:
  - long press on master resets the whole group
  - camera nodes rejoin through master

#### Stage 9 test plan

- [ ] Delete a Pi logical device and verify:
  - device removed
  - related records cleaned up
- [ ] Delete an ESP32 logical device and verify:
  - logical device removed
  - attached nodes removed
  - provisioning mappings released
- [ ] Verify reprovisioning can begin cleanly after delete/reset
- [ ] Pass criteria:
  - no orphaned node mappings remain
  - Pi delete path still works
  - ESP32 group delete behaves as one user action

### Stage 10: master-node provisioning work

- [ ] Define ESP-NOW provisioning payload from master to camera node
- [ ] Include at least:
  - Wi-Fi SSID
  - Wi-Fi password
  - platform URL
  - logical platform device id
  - shared device token
  - camera node index
  - config version
- [ ] Define ACK/retry behavior for camera provisioning
- [ ] Decide whether master provisions:
  - one camera at a time
  - or broadcasts for multiple cameras

#### Stage 10 test plan

- [ ] Verify master can assemble and send provisioning payload
- [ ] Verify master receives ACK or timeout result
- [ ] Test retry behavior on a missing/unresponsive camera
- [ ] Pass criteria:
  - master can start camera provisioning intentionally
  - failures are visible and recoverable
  - no impact on already-working master Wi-Fi/platform behavior

### Stage 11: camera-node provisioning work

- [ ] Add Preferences-backed config storage on camera node
- [ ] Add ESP-NOW receiver for provisioning payload
- [ ] Save received config locally
- [ ] Reboot or reconnect as needed after provisioning payload is applied
- [ ] Add node heartbeat after provisioning succeeds
- [ ] Keep camera invisible to the user as a separate setup surface

#### Stage 11 test plan

- [ ] Verify camera receives provisioning payload via ESP-NOW
- [ ] Verify camera stores config in Preferences
- [ ] Reboot camera and verify config persists
- [ ] Verify camera can connect to Wi-Fi with received credentials
- [ ] Verify camera appears as attached node in website data
- [ ] Pass criteria:
  - no user-facing camera setup page is needed
  - camera becomes a node of the logical device
  - camera survives reboot with stored config

### Stage 12: master-controlled capture scheduling

- [ ] Define ESP-NOW capture command contract
- [ ] Master owns image schedule
- [ ] Camera node only executes capture requests
- [ ] Add optional future messages for:
  - capture now
  - pause capture
  - update interval
- [ ] Keep current standalone camera test firmware only as a development tool, not final product behavior

#### Stage 12 test plan

- [ ] Verify master can send `CAPTURE` command over ESP-NOW
- [ ] Verify camera captures and uploads one image on command
- [ ] Verify idle camera does not self-schedule uploads anymore
- [ ] Verify master timing controls actual capture cadence
- [ ] Pass criteria:
  - image uploads only happen when master intends them to
  - camera returns to idle after upload
  - heartbeat continues even if capture/upload fails

### Stage 13: migration and compatibility testing

- [ ] Verify Raspberry Pi onboarding still works unchanged
- [ ] Verify Raspberry Pi dashboard still works with new node model
- [ ] Verify ESP32 master-only onboarding completes without waiting for image
- [ ] Verify ESP32 device detail page can show missing camera node without looking broken
- [ ] Verify delete/reset works for:
  - Raspberry Pi
  - ESP32 master only
  - ESP32 master plus camera node(s)

#### Stage 13 test plan

- [ ] Run the full Raspberry Pi onboarding and dashboard flow
- [ ] Run the full ESP32 master-only onboarding flow
- [ ] Run ESP32 master + camera local flow
- [ ] Check mixed-account behavior with both device families present
- [ ] Pass criteria:
  - no regression in Pi flow
  - no duplicate logical devices
  - ESP32 grouped device behavior matches product expectations

### Stage 14: rollout order

- [ ] Implement schema/model changes first
- [ ] Then platform APIs
- [ ] Then website detail/list rendering
- [ ] Then ESP32 master registration updates
- [ ] Then camera-node provisioning over ESP-NOW
- [ ] Then master-driven capture scheduling

#### Stage 14 test plan

- [ ] Before each rollout step, confirm previous stage is committed and stable
- [ ] Rebuild local Docker after each platform/web stage
- [ ] Run targeted smoke tests before moving forward
- [ ] Only advance when the current stage passes its criteria
- [ ] Pass criteria:
  - each stage has a clear stop/go checkpoint
  - no bundled multi-stage leap without verification

## Suggested First Working Slice

If we want the safest first implementation slice, do this first:

1. Add node metadata to the backend/platform model
2. Add node summary to device detail page
3. Add node-aware heartbeat
4. Preserve Raspberry Pi behavior unchanged
5. Only then begin master-to-camera provisioning

This gives the website a correct mental model before the camera-node provisioning work starts.

### Suggested first-slice test plan

- [ ] Confirm node metadata can exist without changing user-visible device count
- [ ] Confirm node summary can render without breaking Pi pages
- [ ] Confirm node heartbeat updates node state without overwriting device reading state
- [ ] Pass criteria:
  - website understands grouped hardware
  - Raspberry Pi still feels unchanged
  - platform is ready for camera-node provisioning work

## Guardrails

- Do not break the Raspberry Pi path.
- Do not expose camera nodes as separate devices in the dashboard.
- Do not let camera heartbeats overwrite master-owned device state.
- Do not make ESP32 setup completion depend on camera readiness.
- Do not require users to provision cameras separately.

## One-Sentence Rule to Keep Us Aligned

A PlantLab device is a logical container that may contain one or more hardware nodes, but the user still manages it as one device.
