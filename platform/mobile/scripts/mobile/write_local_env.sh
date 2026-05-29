#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"

API_URL="${EXPO_PUBLIC_API_BASE_URL:-}"
SKIP_BACKEND_CHECK=0
WIFI_SSID_OPTIONS="${EXPO_PUBLIC_WIFI_SSID_OPTIONS:-}"

usage() {
  cat <<'EOF'
Usage: scripts/mobile/write_local_env.sh [options]

Writes platform/mobile/.env for a local PlantLab backend.

Options:
  --api-url URL           Backend URL to write. Example: http://192.168.0.55:8000
  --wifi-ssid-options CSV Optional comma-separated Wi-Fi SSID seed list.
  --skip-backend-check    Do not probe /health after writing .env.
  -h, --help              Show this help.

Environment:
  EXPO_PUBLIC_API_BASE_URL       Optional backend URL override.
  EXPO_PUBLIC_WIFI_SSID_OPTIONS  Optional Wi-Fi SSID seed list.
  PLANTLAB_LOCAL_IFACES          Optional space-separated interface list. Default: en0 en1.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --api-url)
      [[ $# -ge 2 ]] || fail "--api-url requires a value."
      API_URL="$2"
      shift 2
      ;;
    --wifi-ssid-options)
      [[ $# -ge 2 ]] || fail "--wifi-ssid-options requires a value."
      WIFI_SSID_OPTIONS="$2"
      shift 2
      ;;
    --skip-backend-check)
      SKIP_BACKEND_CHECK=1
      shift
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

cd_mobile_dir
require_expo_app

detect_lan_ip() {
  local iface
  for iface in ${PLANTLAB_LOCAL_IFACES:-en0 en1}; do
    if has_command ipconfig; then
      ipconfig getifaddr "$iface" 2>/dev/null || true
    fi
  done | awk 'NF { print; exit }'
}

if [[ -z "$API_URL" ]]; then
  lan_ip="$(detect_lan_ip)"
  if [[ -z "$lan_ip" ]]; then
    fail "Could not detect a LAN IP. Re-run with --api-url http://YOUR_MAC_LAN_IP:8000"
  fi
  API_URL="http://${lan_ip}:8000"
fi

API_URL="${API_URL%/}"

case "$API_URL" in
  http://127.0.0.1:*|http://localhost:*)
    warn "This API URL only works from an iOS simulator. A physical iPhone needs your Mac's LAN IP."
    ;;
esac

cat > .env <<EOF
EXPO_PUBLIC_API_BASE_URL=${API_URL}
EXPO_PUBLIC_AUTH_MODE=dev
EXPO_PUBLIC_ENABLE_DEV_AUTH=true
EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false
EXPO_PUBLIC_WIFI_SSID_OPTIONS=${WIFI_SSID_OPTIONS}
EOF

log "Wrote local mobile environment: ${MOBILE_DIR}/.env"
log "EXPO_PUBLIC_API_BASE_URL=${API_URL}"

if [[ "$SKIP_BACKEND_CHECK" -eq 0 ]]; then
  if has_command curl; then
    if curl -fsS --max-time 3 "${API_URL}/health" >/dev/null; then
      log "Local backend health check passed."
    else
      warn "Could not reach ${API_URL}/health. Start local Docker backend or pass --skip-backend-check."
    fi
  else
    warn "curl is unavailable; skipping backend health check."
  fi
fi
