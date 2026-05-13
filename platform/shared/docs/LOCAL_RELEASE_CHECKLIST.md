# Local Release Checklist

Use this checklist before calling the local PlantLab stack "ready" for a real hardware QA session.

## 1. Backend and contracts

- [ ] Run backend tests

  ```bash
  cd /Users/gary/plantOS/platform/backend
  ../../.venv/bin/python -m pytest -q
  ```

- [ ] Rebuild the local backend container

  ```bash
  cd /Users/gary/plantOS
  docker compose -f docker-compose.local.yml up -d --build platform
  ```

- [ ] Confirm backend health

  ```bash
  curl http://localhost:8000/health
  ```

- [ ] Confirm old backend-rendered login still loads

  ```bash
  curl -I http://localhost:8000/login
  ```

## 2. Standalone web

- [ ] Typecheck standalone web

  ```bash
  cd /Users/gary/plantOS/platform/web
  npm run typecheck
  ```

- [ ] Build standalone web

  ```bash
  cd /Users/gary/plantOS/platform/web
  npm run build
  ```

- [ ] Confirm `.env` points to the local backend

  ```env
  VITE_API_BASE_URL=http://localhost:8000
  ```

- [ ] Smoke standalone login with dev auth
- [ ] Confirm device list loads without mock mode when backend is healthy

## 3. Mobile / Expo

- [ ] Use Node 22 before running Expo

  ```bash
  source ~/.nvm/nvm.sh
  nvm use 22
  ```

- [ ] Typecheck mobile

  ```bash
  cd /Users/gary/plantOS/platform/mobile
  npm run typecheck
  ```

- [ ] Export iOS bundle

  ```bash
  cd /Users/gary/plantOS/platform/mobile
  npx expo export --platform ios
  ```

- [ ] Start Metro for local iPhone QA

  ```bash
  cd /Users/gary/plantOS/platform/mobile
  source ~/.nvm/nvm.sh
  nvm use 22
  npx expo start --clear --host lan
  ```

- [ ] Confirm Expo Go connects on the local network
- [ ] Confirm the mobile app can load the real backend device list

## 4. ESP32 compile / flash

- [ ] Compile master firmware

  ```bash
  cd /Users/gary/plantOS/device/esp32
  PLATFORMIO_CORE_DIR=/Users/gary/plantOS/.pio-core /Users/gary/plantOS/.venv/bin/pio run
  ```

- [ ] Reflash master if needed

  ```bash
  cd /Users/gary/plantOS/device/esp32
  ./scripts/flash_esp32.sh --local --monitor
  ```

- [ ] Reflash camera node if needed

  ```bash
  cd /Users/gary/plantOS/device/esp32
  ./scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem112201 --monitor
  ```

## 5. Hardware loop smoke

- [ ] Heartbeat is arriving
- [ ] Reading uploads are arriving
- [ ] Image uploads are arriving
- [ ] Latest reading timestamp advances over time
- [ ] Latest image timestamp advances over time
- [ ] Hardware Health panel shows the expected master/camera status

Helpful local checks:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/backend_health_check.py --include-dev-login
.venv/bin/python platform/infra/scripts/device_summary_dump.py --device-id 36
.venv/bin/python platform/infra/scripts/recent_readings_dump.py --device-id 36 --limit 5
.venv/bin/python platform/infra/scripts/image_upload_inspector.py --device-id 36 --limit 5
```

## 6. Command execution smoke

- [ ] Send light on from standalone web or mobile
- [ ] Confirm command status moves through queued/pending/in-progress/completed
- [ ] Confirm ESP32 serial log shows command handling
- [ ] Confirm latest reading or device summary reflects the new light state
- [ ] Send light off and confirm the system returns to baseline
- [ ] Send a short pump run and confirm it completes cleanly

Helpful local check:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/command_queue_inspector.py --device-id 36 --limit 8
```

## 7. Onboarding smoke

- [ ] Put the master into provisioning mode
- [ ] Connect the laptop or phone to `PlantLab-Setup`
- [ ] Open the generated `10.42.0.1:8080` setup URL
- [ ] Submit home Wi-Fi credentials
- [ ] Confirm setup-finishing eventually redirects to the standalone dashboard
- [ ] Confirm the new device appears under the same standalone account used for onboarding

Notes:

- the `10.42.0.1:8080` page may take 20-30 seconds to become reachable after the Wi-Fi switch
- Safari is often more reliable than Chrome on a no-internet AP

## 8. Mock fallback smoke

- [ ] Stop the backend
- [ ] Confirm standalone web falls back to mock mode visibly
- [ ] Confirm standalone mobile falls back to mock mode visibly if tested
- [ ] Restart the backend and confirm real mode returns after a fresh load or session refresh

## Common failure symptoms

### Symptom: standalone web shows `Mock mode` even though the backend is up

- likely causes:
  - missing `platform/web/.env`
  - stale mock session in `localStorage`
  - local backend CORS/container is stale
- quick recovery:
  - confirm `VITE_API_BASE_URL=http://localhost:8000`
  - rebuild backend container
  - clear `localStorage.removeItem("plantlab.web.session")`
  - sign in again

### Symptom: `10.42.0.1:8080` takes a long time to open

- likely causes:
  - laptop/browser Wi-Fi handoff delay on a no-internet AP
- quick recovery:
  - wait 20-30 seconds after joining `PlantLab-Setup`
  - paste the full setup URL into Safari manually

### Symptom: setup-finishing waits forever for device readiness

- likely causes:
  - master registered under the wrong user
  - backend container is running stale code
  - camera node is not online when an image is expected
- quick recovery:
  - rebuild backend container
  - confirm the standalone account owns the new device
  - check master and camera serial logs
  - inspect summary output with `device_summary_dump.py`

### Symptom: hardware endpoints return `401 Valid device token required`

- likely causes:
  - the backend device was deleted after provisioning
  - the ESP32 still has a stale device token in Preferences
- quick recovery:
  - factory reset or re-provision the board
  - add the device again from standalone web

### Symptom: dashboard health looks offline or stale while readings are expected

- likely causes:
  - master heartbeat stopped
  - camera heartbeat stopped
  - backend container restarted while hardware kept an old token
- quick recovery:
  - inspect live summary and readings with the local scripts
  - check serial logs on master and camera
  - re-onboard the board if the token no longer matches a live backend device

### Symptom: Expo local QA fails or Metro behaves strangely

- likely causes:
  - wrong Node version
- quick recovery:
  - use Node 22
  - restart Expo with `npx expo start --clear --host lan`
