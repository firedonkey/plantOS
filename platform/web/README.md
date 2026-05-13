# Web

This folder is reserved for the standalone PlantLab browser frontend.

Final intent:

- standalone frontend app
- talks to backend only through API endpoints
- fully replaces backend-rendered web routes in Stage 2

Local dev:

- Copy [`.env.example`](/Users/gary/plantOS/platform/web/.env.example) to `.env` if needed.
- Set `VITE_API_BASE_URL` to your local backend, usually `http://localhost:8000`.
- Use `VITE_AUTH_MODE=production` for backend-owned Google auth.
- Use `VITE_AUTH_MODE=dev` with `VITE_ENABLE_DEV_AUTH=true` only for local dev bearer login.
- Leave `VITE_ENABLE_MOCK_FALLBACK=false` for real hardware QA. Set it to `true` only when you explicitly want bundled mock data.
- Start the standalone app with `npm run dev`.
- Keep this app running side-by-side with the backend-rendered web during migration.

Status:

- standalone React/Vite frontend scaffold is in place
- uses backend APIs when available
- uses backend Google auth and refresh cookies in production mode
- does not silently switch to mock data by default when the backend is unavailable
- mock fallback remains available only when `VITE_ENABLE_MOCK_FALLBACK=true`
- does not replace backend-rendered web routes yet
- manual image capture is intentionally postponed for now
- the standalone UI treats capture as a coming-later capability instead of a broken action

Manual test checklist:

- Backend-rendered web still loads at `http://localhost:8000/devices`
- Standalone web loads at the Vite dev URL
- Dev login works against `POST /api/auth/login`
- Production login starts at `GET /api/auth/google/start` and restores through `POST /api/auth/refresh`
- Device list loads from the backend when the backend is running
- Add-device flow verifies an SN and shows the Wi-Fi/setup-finishing handoff
- Setup-finishing flow polls until the device is ready, then opens the standalone dashboard
- Dashboard loads summary, readings, and latest image from the backend
- Light and pump commands return success feedback
- Remove-device flow shows confirmation and removes a device through the standalone API
- Capture command shows the expected friendly unsupported message
- Backend-down states stay visible by default
- Mock mode still works when `VITE_ENABLE_MOCK_FALLBACK=true`

Onboarding troubleshooting:

- After joining `PlantLab-Setup`, macOS may need 20-30 seconds before `http://10.42.0.1:8080` becomes reachable.
- If the browser warns that the Wi-Fi has no internet, stay on the access point and retry the setup page after the network switch settles.
- Leave the standalone setup-finishing page open until it reports the first reading. If image setup is still pending after the reading arrives, check the camera node power, firmware, and ESP-NOW logs.
