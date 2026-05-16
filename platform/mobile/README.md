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
- Local dev builds use the username/password form when `EXPO_PUBLIC_AUTH_MODE=dev` and `EXPO_PUBLIC_ENABLE_DEV_AUTH=true`.
- For local username login, `dev` becomes `dev@plantlab.local`; an email address is used as-is. The password must be non-empty and is only for dev-token login against a local backend.
- Do not point dev-token login at the production backend. Production Cloud Run has `PLANTLAB_DEV_TOKEN_AUTH_ENABLED=false`, so production builds should use `EXPO_PUBLIC_AUTH_MODE=production` and Google sign-in.
- Google sign-in is available from the mobile login screen and uses the backend-owned `/api/auth/google/start` handoff.
- The mobile callback uses the app scheme `plantlab://auth/callback`. Expo Go may not claim custom app schemes reliably; use a dev build or installed app build when validating the full callback loop.
- Leave `EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false` for real hardware QA. Set it to `true` only when you explicitly want bundled mock data.
- Optional: set `EXPO_PUBLIC_WIFI_SSID_OPTIONS=HomeWiFi,LabWiFi` to seed the add-device Wi-Fi dropdown.
- During BLE device setup, tap `Load nearby Wi-Fi over BLE` to populate the mobile dropdown from the ESP32 BLE scan cache. This requires a native development build because Expo Go cannot load the BLE native module.
- The `PlantLab-Setup` SoftAP page remains available as a compatibility fallback. Manual SSID entry remains available in both flows.
- iOS simulator can use `http://127.0.0.1:8000`
- physical devices should use your Mac's LAN IP, for example `http://192.168.x.x:8000`
- Restart Metro after changing `EXPO_PUBLIC_*` values. Rebuild the development client after changing native dependencies, app permissions, bundle ID, or config plugins.

Expo Go vs native development builds:

- `npm start` keeps the Expo Go workflow available for UI-only development.
- BLE, installed-app scheme handling, native permission prompts, and real iPhone behavior require an installed development build.
- Start Metro for the installed development build with `npm run start:dev`.

iOS development build prerequisites:

- Apple Developer Program access is required for installing on a real iPhone.
- Use an Apple account with permission to create or use the App ID, signing certificate, provisioning profile, and registered device UDID.
- The iOS bundle identifier is `com.plantlab.mobile`.
- The app scheme remains `plantlab` for callbacks such as `plantlab://auth/callback`.
- EAS-managed credentials are the default path. Local Xcode builds are optional for developers with Xcode, CocoaPods, and signing already configured.

First-time EAS setup:

```bash
cd platform/mobile
npm install
npx eas login
npx eas init
```

`npx eas init` links this app to an Expo/EAS project and may add `extra.eas.projectId` to `app.json`. Do not add a placeholder project ID manually.

Register a real iPhone for internal development builds:

```bash
cd platform/mobile
npm run register:ios
```

Open the EAS registration link or QR code on the iPhone, install the device registration profile, then return to the terminal.

Build and install on a real iPhone:

```bash
cd platform/mobile
npm run build:ios:dev
```

The build script verifies EAS CLI access, EAS login, `eas.json`, `expo-dev-client`, typecheck when available, and Expo config before starting `eas build --profile development --platform ios`.

To validate the local setup without starting a cloud build:

```bash
cd platform/mobile
bash scripts/mobile/build_ios_dev.sh --check-only
```

Follow the EAS prompts to register the iPhone if needed, then install the internal build from the EAS result page. After installation, start Metro for the installed development client:

```bash
cd platform/mobile
npm run start:dev
```

`npm run start:dev` clears Watchman/Metro cache state, raises the file descriptor limit for the shell when possible, and runs Expo with `--dev-client --host lan`.

Open the installed PlantLab development build on the iPhone, not Expo Go, and connect it to the LAN Metro server. For physical-device backend QA, set `EXPO_PUBLIC_API_BASE_URL` to the Mac's LAN address, not `127.0.0.1`.

Local backend auth setup for iPhone QA:

```bash
cd platform/mobile
cat > .env <<'EOF'
EXPO_PUBLIC_API_BASE_URL=http://192.168.0.55:8000
EXPO_PUBLIC_AUTH_MODE=dev
EXPO_PUBLIC_ENABLE_DEV_AUTH=true
EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false
EOF
npm run start:dev
```

Restart Metro after changing `.env`. The login screen should show username/password only. Use `dev` / `password` or any username with a non-empty password.

Recover from Metro watcher/cache issues:

```bash
cd platform/mobile
npm run clean:metro
npm run start:dev
```

See [`docs/mobile_troubleshooting.md`](docs/mobile_troubleshooting.md) for EMFILE, Watchman, Metro cache, Expo Go vs development build, iOS Developer Mode, Apple signing, and EAS login issues.

Optional simulator build:

```bash
cd platform/mobile
npm run build:ios:sim
```

Optional local iOS run for developers with native tooling:

```bash
cd platform/mobile
npx expo run:ios --device
```

Native capability validation checklist:

- App startup: installed development build launches to the expected login/navigation flow.
- API config: physical iPhone points at the intended LAN backend URL.
- Auth/session: dev login works; Google handoff returns through `plantlab://auth/callback`; logout clears the session.
- Storage: AsyncStorage-backed dev sessions behave as before; production refresh-token persistence remains disabled until secure storage is added.
- BLE provisioning: native build loads `react-native-ble-plx`, requests Bluetooth permission, scans for `PlantLab-Setup`, reads nearby Wi-Fi names, sends credentials, and waits for the ESP32 to validate Wi-Fi before backend polling starts. Wrong passwords should stay on the Wi-Fi screen with an immediate BLE error.
- Camera/QR: camera permission prompt appears and the QR scanner can populate the device serial number.
- Image gallery: remote recent images still load with auth headers when required.
- SoftAP/local network: fallback setup page can be opened and the local network prompt is validated if iOS shows it.
- Rebuild rule: native dependency or permission changes require a rebuilt development client.

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
