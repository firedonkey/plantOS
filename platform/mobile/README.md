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
- iOS simulator can use `http://127.0.0.1:8000`
- physical devices should use your Mac's LAN IP, for example `http://192.168.x.x:8000`

Status:

- Expo app scaffold is in place
- tries the local backend first
- falls back to mock mode when the backend is unavailable
