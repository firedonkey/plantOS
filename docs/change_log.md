# Change Log

This is an append-only record of completed tasks and runs.

## 2026-05-17

- Removed the legacy `agent-workspace/` folder in favor of Pantheon-managed project state.

## 2026-05-19

- Added capability-gated grow LED intensity control across backend commands/readings/status, ESP32 firmware, and web/mobile dashboards while preserving existing on/off control.
- Added end-to-end ESP32 water temperature and water level reading support across firmware payloads, backend storage/API schemas, and dashboard displays.

<!-- pantheon-memory:20260519T202340Z:20260519_202340_continue_the_current_led_illumin:change-log -->
## 2026-05-19T20:47:26.515144+00:00 - 20260519_202340_continue_the_current_led_illumin

- Task: Continue the current LED illumination task. Preserve all existing uncommitted...
- Run: `20260519T202340Z`
- Execution mode: `target_project`
- Summary: Reviewer approved the implementation.
- Scope decision: `target_project`
- Risk level: `medium`
- Protected area touched: `false`
- Project mode: `existing_project_with_context`
- Context quality: `outdated`
- Files likely affected:
- (none)
- Current changed files:
-  M device/esp32/include/config.h
-  M device/esp32/src/actuators/light_controller.cpp
-  M device/esp32/src/actuators/light_controller.h
-  M device/esp32/src/main.cpp
-  M device/esp32/src/platform/platform_client.cpp
-  M device/esp32/src/platform/platform_client.h
-  M device/esp32/src/tests/actuators_test_main.cpp
-  M device/esp32/tests_host/test_platform_client_heartbeat.cpp
-  M docs/change_log.md
-  M docs/decision_log.md
-  M docs/design/api_contract.md
-  M docs/project_brief.md
-  M platform/backend/app/api/routes/device_nodes.py
-  M platform/backend/app/api/routes/devices.py
-  M platform/backend/app/api/routes/hardware.py
-  M platform/backend/app/db/session.py
-  M platform/backend/app/models/command.py
-  M platform/backend/app/models/device.py
-  M platform/backend/app/models/sensor_reading.py
-  M platform/backend/app/schemas/commands.py
-  M platform/backend/app/schemas/device_nodes.py
-  M platform/backend/app/schemas/devices.py
-  M platform/backend/app/schemas/hardware.py
-  M platform/backend/app/schemas/readings.py
-  M platform/backend/app/schemas/status.py
-  M platform/backend/app/services/commands.py
-  M platform/backend/app/services/device_nodes.py
-  M platform/backend/app/services/readings.py
-  M platform/backend/app/services/status.py
-  M platform/backend/app/web/routes.py
-  M platform/backend/app/web/static/style.css
-  M platform/backend/app/web/templates/device_detail.html
-  M platform/backend/tests/test_commands.py
-  M platform/backend/tests/test_device_nodes_api.py
-  M platform/backend/tests/test_devices.py
-  M platform/backend/tests/test_hardware_api.py
-  M platform/backend/tests/test_readings.py
-  M platform/mobile/src/api/devices.ts
-  M platform/mobile/src/components/CommandActivityPanel.tsx
-  M platform/mobile/src/components/HardwareHealthPanel.tsx
-  M platform/mobile/src/hooks/useDeviceDashboard.ts
-  M platform/mobile/src/mock/data.ts
-  M platform/mobile/src/screens/DeviceDashboardScreen.tsx
-  M platform/mobile/src/types/api.ts
-  M platform/mobile/test/mobileDashboardPolish.test.ts
-  M platform/web/src/api/devices.ts
-  M platform/web/src/components/CommandActivityPanel.tsx
-  M platform/web/src/components/HardwareHealthPanel.tsx
-  M platform/web/src/hooks/useDeviceDashboard.ts
-  M platform/web/src/mock/data.ts
-  M platform/web/src/screens/DeviceDashboardScreen.tsx
-  M platform/web/src/styles/app.css
-  M platform/web/src/types/api.ts
- ?? conftest.py
- ?? platform/backend/migrations/versions/20260519_0009_light_intensity.py
- ?? platform/web/test/
- ?? test_pytest_raspberry_pi_guard.py
- Tests/checks: see `agent-workspace/outputs/20260519_202340_continue_the_current_led_illumin/test_report.md` and `runs/20260519T202340Z/events.jsonl`
- Memory updates expected:
- docs/change_log.md
- Risks or follow-ups: Planner, Coder, Tester, and Reviewer must not expand this scope. If scope needs to change, stop and request a new Architect task.

<!-- pantheon-memory:20260519T235300Z:20260519_235300_fix_plantos_sensor_trends_the_wa:change-log -->
## 2026-05-20T00:09:43.980964+00:00 - 20260519_235300_fix_plantos_sensor_trends_the_wa

- Task: Fix PlantOS sensor trends: the water temperature chart currently shows no dat...
- Run: `20260519T235300Z`
- Execution mode: `target_project`
- Summary: Reviewer approved the implementation.
- Scope decision: `target_project`
- Risk level: `medium`
- Protected area touched: `false`
- Project mode: `existing_project_with_context`
- Context quality: `good_enough`
- Files likely affected:
- (none)
- Current changed files:
-  M platform/backend/app/web/routes.py
-  M platform/backend/tests/test_devices.py
-  M platform/mobile/src/components/ReadingTrendSection.tsx
-  M platform/mobile/test/sensorTrendLineChart.test.ts
-  M platform/web/src/components/ReadingTrendSection.tsx
-  M platform/web/test/webWaterReadings.test.js
- Tests/checks: see `agent-workspace/outputs/20260519_235300_fix_plantos_sensor_trends_the_wa/test_report.md` and `runs/20260519T235300Z/events.jsonl`
- Memory updates expected:
- docs/change_log.md
- docs/project_brief.md
- Risks or follow-ups: Planner, Coder, Tester, and Reviewer must not expand this scope. If scope needs to change, stop and request a new Architect task.
