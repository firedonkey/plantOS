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
- Leave `EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false` for real hardware QA. Set it to `true` only when you explicitly want bundled mock data.
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
- does not silently switch to mock data by default when the backend is unavailable
- mock fallback remains available only when `EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=true`
- manual image capture is intentionally postponed for now
- the mobile UI treats capture as a coming-later capability instead of a failed command
