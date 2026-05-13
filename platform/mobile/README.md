# Mobile

This folder is reserved for the PlantLab Expo mobile app.

Scope:

- iOS first
- Android later from the same shared codebase
- uses backend APIs instead of embedding backend logic

Plan:

- [Mobile App Plan](/Users/gary/plantOS/platform/mobile/MOBILE_APP_PLAN.md)

Local dev:

- Set `EXPO_PUBLIC_API_BASE_URL` to your backend base URL.
- Use [`.env.example`](/Users/gary/plantOS/platform/mobile/.env.example) as the starting point.
- Keep `EXPO_PUBLIC_AUTH_MODE=dev` for local dev bearer login.
- Google sign-in is available from the mobile login screen and uses the backend-owned `/api/auth/google/start` handoff.
- The mobile callback uses the app scheme `plantlab://auth/callback`. Expo Go may not claim custom app schemes reliably; use a dev build or installed app build when validating the full callback loop.
- Leave `EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false` for real hardware QA. Set it to `true` only when you explicitly want bundled mock data.
- Optional: set `EXPO_PUBLIC_WIFI_SSID_OPTIONS=HomeWiFi,LabWiFi` to seed the add-device Wi-Fi dropdown.
- During real device setup, connect the phone to `PlantLab-Setup`, then tap `Load nearby Wi-Fi from device` to populate the mobile dropdown from the ESP32 scan cache. Manual SSID entry remains available.
- iOS simulator can use `http://127.0.0.1:8000`
- physical devices should use your Mac's LAN IP, for example `http://192.168.x.x:8000`

Mobile local QA setup:

- Use Node LTS before starting Expo:

```bash
nvm use 22
```

- Expected:
  - `node -v` -> `v22.22.2` or another Node 22 LTS version

- Start mobile:

```bash
cd platform/mobile
npx expo start --clear --host lan
```

- Expected Metro URL:
  - `exp://192.168.0.55:8081`

- Backend API for iPhone:
  - `EXPO_PUBLIC_API_BASE_URL=http://192.168.0.55:8000`

- Do not use Node v25 for Expo local QA.

Status:

- Expo app scaffold is in place
- tries the local backend first
- includes API helpers for backend Google start URL, handoff refresh exchange, production refresh, and logout
- handles backend Google handoff callbacks at `plantlab://auth/callback`
- does not persist production refresh credentials because `expo-secure-store` is not installed yet
- does not silently switch to mock data by default when the backend is unavailable
- mock fallback remains available only when `EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=true`
- supports manual image capture from the recent image gallery
