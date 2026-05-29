#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROFILE="${EAS_PROFILE:-development-local}"
LOCAL_ENV_ARGS=()
BUILD_ARGS=()

usage() {
  cat <<'EOF'
Usage: scripts/mobile/build_ios_local.sh [options] [extra eas build args...]

Writes local mobile API config, then builds an iOS development client profile
intended for local backend QA.

Options:
  --profile NAME          EAS profile. Default: development-local
  --api-url URL           Backend URL. Example: http://192.168.0.55:8000
  --wifi-ssid-options CSV Optional comma-separated Wi-Fi SSID seed list.
  --skip-backend-check    Do not probe /health before build.
  --check-only            Verify setup without starting an EAS build.
  -h, --help              Show this help.

Examples:
  npm run build:ios:local -- --api-url http://192.168.0.55:8000
  npm run build:ios:local -- --check-only
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --profile)
      [[ $# -ge 2 ]] || {
        printf '[mobile][FAIL] --profile requires a value.\n' >&2
        exit 1
      }
      PROFILE="$2"
      shift 2
      ;;
    --api-url|--wifi-ssid-options)
      [[ $# -ge 2 ]] || {
        printf '[mobile][FAIL] %s requires a value.\n' "$1" >&2
        exit 1
      }
      LOCAL_ENV_ARGS+=("$1" "$2")
      shift 2
      ;;
    --skip-backend-check)
      LOCAL_ENV_ARGS+=("$1")
      shift
      ;;
    *)
      BUILD_ARGS+=("$1")
      shift
      ;;
  esac
done

"${SCRIPT_DIR}/write_local_env.sh" "${LOCAL_ENV_ARGS[@]}"
"${SCRIPT_DIR}/build_ios_dev.sh" --profile "$PROFILE" "${BUILD_ARGS[@]}"
