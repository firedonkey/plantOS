#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"

PROFILE="${EAS_PROFILE:-development}"
RUN_TYPECHECK="${RUN_TYPECHECK:-1}"
RUN_EXPO_CONFIG="${RUN_EXPO_CONFIG:-1}"
CHECK_ONLY=0
EXTRA_EAS_ARGS=()

usage() {
  cat <<'EOF'
Usage: scripts/mobile/build_ios_dev.sh [options] [extra eas build args...]

Builds an Expo/EAS native iOS development client.

Options:
  --profile NAME          EAS profile to use. Default: development
  --skip-typecheck       Do not run package.json typecheck script.
  --skip-expo-config     Do not run Expo config validation.
  --check-only           Verify prerequisites and config, but do not start a build.
  -h, --help             Show this help.

Environment:
  MOBILE_APP_DIR=/path/to/expo-app   Optional explicit Expo app directory.
  EAS_PROFILE=development            Default EAS profile.
  RUN_TYPECHECK=0                    Skip typecheck.
  RUN_EXPO_CONFIG=0                  Skip Expo config validation.

Examples:
  scripts/mobile/build_ios_dev.sh
  scripts/mobile/build_ios_dev.sh --profile development --non-interactive
  MOBILE_APP_DIR=platform/mobile scripts/mobile/build_ios_dev.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --profile)
      [[ $# -ge 2 ]] || fail "--profile requires a value."
      PROFILE="$2"
      shift 2
      ;;
    --skip-typecheck)
      RUN_TYPECHECK=0
      shift
      ;;
    --skip-expo-config)
      RUN_EXPO_CONFIG=0
      shift
      ;;
    --check-only)
      CHECK_ONLY=1
      shift
      ;;
    *)
      EXTRA_EAS_ARGS+=("$1")
      shift
      ;;
  esac
done

cd_mobile_dir
require_expo_app
require_node_modules
require_eas_json
require_eas_cli
require_eas_login

if ! package_has_dependency expo-dev-client; then
  fail "expo-dev-client is missing. Install it with: npx expo install expo-dev-client"
fi

if [[ "$RUN_TYPECHECK" != "0" ]]; then
  if package_has_script typecheck; then
    log "Running typecheck before iOS development build."
    run_package_script typecheck
  else
    warn "No package.json typecheck script found; skipping typecheck."
  fi
else
  warn "Skipping typecheck because RUN_TYPECHECK=0 or --skip-typecheck was set."
fi

if [[ "$RUN_EXPO_CONFIG" != "0" ]]; then
  log "Validating Expo public config."
  run_expo config --type public >/dev/null
  log "Expo public config is valid."
else
  warn "Skipping Expo config validation."
fi

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  log "Check-only mode complete. No EAS build was started."
  exit 0
fi

log "Starting EAS iOS development build."
log "Profile: ${PROFILE}"
if [[ "${#EXTRA_EAS_ARGS[@]}" -gt 0 ]]; then
  run_eas build --profile "$PROFILE" --platform ios "${EXTRA_EAS_ARGS[@]}"
else
  run_eas build --profile "$PROFILE" --platform ios
fi
