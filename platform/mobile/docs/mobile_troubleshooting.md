# Mobile Troubleshooting

This guide is for Expo/EAS native development builds used with PlantLab mobile app scripts.

The scripts are generic. They do not assume a specific app name, backend URL, Apple team, Expo account, or cloud provider.

## App Discovery

Scripts try to find an Expo app automatically. If discovery is ambiguous, set:

```bash
export MOBILE_APP_DIR=/path/to/expo-app
```

Then run:

```bash
scripts/mobile/build_ios_dev.sh --check-only
```

## EMFILE: Too Many Open Files

Symptom:

```text
EMFILE: too many open files, watch
```

Likely causes:

- Metro is watching too many files.
- Old Metro/Watchman state is stale.
- Multiple Metro servers are running.
- macOS file descriptor limit is too low for the current shell.

Recovery:

```bash
MOBILE_APP_DIR=/path/to/expo-app scripts/mobile/clean_metro_cache.sh
ulimit -n 10240
MOBILE_APP_DIR=/path/to/expo-app scripts/mobile/start_dev_client.sh --host lan
```

If it still fails:

```bash
pkill -f "expo start"
pkill -f "metro"
```

Then start again.

## Watchman Missing

Symptom:

```text
watchman: command not found
```

PlantLab mobile scripts continue without Watchman, but installing it usually improves Metro reliability:

```bash
brew install watchman
```

Then:

```bash
watchman watch-del-all
```

## Metro Cache Issues

Symptoms:

- stale bundle
- changed code not reflected
- confusing module resolution errors
- native dev client cannot connect after dependency/config changes

Recovery:

```bash
MOBILE_APP_DIR=/path/to/expo-app scripts/mobile/clean_metro_cache.sh
MOBILE_APP_DIR=/path/to/expo-app scripts/mobile/start_dev_client.sh --host lan --clear
```

If native dependencies, permissions, or config plugins changed, rebuild the development app. Restarting Metro is not enough.

## Expo Go vs Development Build

Expo Go is useful for UI-only work, but it cannot include arbitrary native modules from your project.

Use a native development build for:

- Bluetooth/BLE libraries
- custom config plugins
- native permission validation
- real app scheme/deep link behavior
- native module compatibility checks

Use Expo Go only when the feature does not depend on project-specific native code.

## iOS Developer Mode

Recent iOS versions may require Developer Mode before a locally installed development app can run.

On the iPhone:

```text
Settings -> Privacy & Security -> Developer Mode
```

Enable it and reboot if iOS asks.

## Apple Signing Issues

Common causes:

- Apple Developer Program membership is missing.
- The Apple account lacks permission to manage certificates/profiles.
- The app bundle identifier conflicts with an existing App ID.
- The target iPhone is not registered for the internal build.
- EAS credentials are not configured for the Expo project.

Recovery:

```bash
npx --yes eas-cli login
npx --yes eas-cli whoami
npx --yes eas-cli credentials
MOBILE_APP_DIR=/path/to/expo-app scripts/mobile/register_ios_device.sh
```

For a new project, run `npx --yes eas-cli init` from the Expo app directory before building.

## EAS Login Issues

Symptoms:

```text
You are not logged in
Authentication required
```

Recovery:

```bash
npx --yes eas-cli login
npx --yes eas-cli whoami
```

Do not paste EAS tokens, Apple passwords, session cookies, or recovery codes into task files, prompts, progress logs, or chat.

## Device Registration Flow

Run:

```bash
MOBILE_APP_DIR=/path/to/expo-app scripts/mobile/register_ios_device.sh
```

EAS will show a link or QR code. Open it on the iPhone, install the device registration profile, then return to the terminal.

## Build Flow

Run:

```bash
MOBILE_APP_DIR=/path/to/expo-app scripts/mobile/build_ios_dev.sh
```

The script verifies:

- EAS CLI access
- EAS login
- `eas.json`
- `expo-dev-client`
- optional `typecheck`
- Expo config parsing

Then it starts:

```bash
eas build --profile development --platform ios
```

Use `--check-only` to validate setup without starting a cloud build.

## Local Backend Build Flow

If a previously installed app is still pointed at GCP, build/start the local
development workflow instead:

```bash
cd platform/mobile
npm run build:ios:local -- --api-url http://YOUR_MAC_LAN_IP:8000
npm run start:dev:local -- --api-url http://YOUR_MAC_LAN_IP:8000
```

The local script writes `platform/mobile/.env` with:

```text
EXPO_PUBLIC_API_BASE_URL=http://YOUR_MAC_LAN_IP:8000
EXPO_PUBLIC_AUTH_MODE=dev
EXPO_PUBLIC_ENABLE_DEV_AUTH=true
EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false
```

For the iOS simulator only, `http://127.0.0.1:8000` is valid. A physical iPhone
needs the Mac's LAN IP and must be able to reach the local Docker backend.

## Device Already Registered To Another Account

Symptom:

```text
This PlantLab is already registered to another account.
```

This means the ESP32 reached the backend, but the backend refused the setup
claim because the hardware ID is already attached to a different user account.
PlantLab transfers ownership only when the ESP32 reports that it was locally
factory reset before the new provisioning attempt.

Recovery options:

- Sign in as the account that currently owns the device and release/remove it.
- Hold the device button for 20 seconds to factory reset it, wait for reboot,
  then add it again from the new account.
- For local-only test data, fix or clear the stale local DB ownership before
  retrying setup.

## Start Dev Client

After installing the native development build on the iPhone:

```bash
MOBILE_APP_DIR=/path/to/expo-app scripts/mobile/start_dev_client.sh --host lan
```

Open the installed development app, not Expo Go.

The iPhone and development machine should be on the same network unless you use a tunnel.

## Future Areas

Not implemented yet:

- Android development builds
- preview builds
- production builds
- TestFlight upload
- CI/CD build pipelines
