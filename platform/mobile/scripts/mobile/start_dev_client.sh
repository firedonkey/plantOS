#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"

SKIP_CLEAN=0
EXPO_ARGS=("--dev-client")

usage() {
  cat <<'EOF'
Usage: scripts/mobile/start_dev_client.sh [--skip-clean] [expo start args...]

Starts Metro for an installed Expo development client.

Examples:
  scripts/mobile/start_dev_client.sh
  scripts/mobile/start_dev_client.sh --host lan
  MOBILE_APP_DIR=platform/mobile scripts/mobile/start_dev_client.sh --host lan --port 8082

Environment:
  MOBILE_APP_DIR=/path/to/expo-app   Optional explicit Expo app directory.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --skip-clean)
      SKIP_CLEAN=1
      shift
      ;;
    *)
      EXPO_ARGS+=("$1")
      shift
      ;;
  esac
done

cd_mobile_dir
require_expo_app
require_node_modules

if [[ "$SKIP_CLEAN" -eq 0 ]]; then
  log "Running Metro cache cleanup before starting the dev client."
  MOBILE_APP_DIR="$MOBILE_DIR" "${SCRIPT_DIR}/clean_metro_cache.sh"
else
  warn "Skipping Metro cache cleanup."
fi

if ulimit -n 10240 >/dev/null 2>&1; then
  log "Set file descriptor limit to 10240 for this shell."
else
  warn "Could not raise file descriptor limit. If Metro reports EMFILE, raise ulimit manually."
fi

if ! package_has_dependency expo-dev-client; then
  warn "expo-dev-client is not listed in package.json. Install it before using a native dev client: npx expo install expo-dev-client"
fi

log "Starting Expo development client Metro server."
log "Command: npx expo start ${EXPO_ARGS[*]}"
run_expo start "${EXPO_ARGS[@]}"
