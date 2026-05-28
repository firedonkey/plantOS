#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8000}"
REPORT_DIR="${REPORT_DIR:-$ROOT_DIR/stress-reports/local-esp32-$(date +%Y%m%d-%H%M%S)}"
SINCE="${SINCE:-30m}"
MIN_HEARTBEATS="${MIN_HEARTBEATS:-1}"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-plantlab-local-postgres}"
POSTGRES_USER="${POSTGRES_USER:-plantlab_user}"
POSTGRES_DB="${POSTGRES_DB:-plantlab}"
PLATFORM_CONTAINER="${PLATFORM_CONTAINER:-plantlab-local-platform}"

mkdir -p "$REPORT_DIR"

fail() {
  echo "[esp32-smoke] ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

psql_query() {
  docker exec -i "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -P pager=off "$@"
}

detect_device() {
  if [[ -n "${DEVICE_ID:-}" && -n "${DEVICE_TOKEN:-}" ]]; then
    return
  fi
  local row
  row="$(psql_query -Atc "select id || '|' || api_token from devices where api_token is not null order by id limit 1;")"
  [[ -n "$row" ]] || fail "no local device with api_token found"
  DEVICE_ID="${DEVICE_ID:-${row%%|*}}"
  DEVICE_TOKEN="${DEVICE_TOKEN:-${row#*|}}"
  export DEVICE_ID DEVICE_TOKEN
}

login_token() {
  python3 - "$BASE_URL" <<'PY'
import json
import sys
import urllib.request

base_url = sys.argv[1].rstrip("/")
payload = json.dumps({"email": "dev@plantlab.local", "password": "password"}).encode()
request = urllib.request.Request(
    f"{base_url}/api/auth/login",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=10) as response:
    print(json.load(response)["token"])
PY
}

require_cmd curl
require_cmd docker
require_cmd python3

docker ps --format '{{.Names}}' | grep -qx "$POSTGRES_CONTAINER" || fail "$POSTGRES_CONTAINER is not running"
docker ps --format '{{.Names}}' | grep -qx "$PLATFORM_CONTAINER" || fail "$PLATFORM_CONTAINER is not running"

curl -fsS "$BASE_URL/health" > "$REPORT_DIR/health.json"
detect_device

node_filter=""
if [[ -n "${EXPECTED_HARDWARE_ID:-}" ]]; then
  node_filter=" and hardware_device_id = '$EXPECTED_HARDWARE_ID'"
fi

psql_query -c "select hardware_device_id, node_role, hardware_model, software_version, status, last_seen_at, ota_status, ota_target_version, ota_progress, ota_error from device_hardware_ids where device_id = $DEVICE_ID $node_filter order by node_role, hardware_device_id;" \
  | tee "$REPORT_DIR/nodes.txt"

heartbeat_count="$(psql_query -Atc "select count(*) from device_diagnostic_events where device_id = $DEVICE_ID and event_type = 'HEARTBEAT_RECEIVED' and occurred_at >= now() - interval '$SINCE' $node_filter;")"
echo "[esp32-smoke] heartbeat_count=$heartbeat_count since=$SINCE"
[[ "$heartbeat_count" -ge "$MIN_HEARTBEATS" ]] || fail "heartbeat_count $heartbeat_count is below MIN_HEARTBEATS=$MIN_HEARTBEATS"

if [[ -n "${EXPECTED_VERSION:-}" ]]; then
  version_count="$(psql_query -Atc "select count(*) from device_hardware_ids where device_id = $DEVICE_ID $node_filter and software_version = '$EXPECTED_VERSION';")"
  [[ "$version_count" -gt 0 ]] || fail "no matching node reports EXPECTED_VERSION=$EXPECTED_VERSION"
fi

psql_query -c "select event_type, count(*) from device_diagnostic_events where device_id = $DEVICE_ID and occurred_at >= now() - interval '$SINCE' $node_filter group by event_type order by count desc, event_type;" \
  | tee "$REPORT_DIR/event_counts.txt"

TOKEN="$(login_token)"
timeline_status="$(
  curl -sS -o "$REPORT_DIR/timeline.json" -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL/api/devices/$DEVICE_ID/timeline?limit=50"
)"
[[ "$timeline_status" == "200" ]] || fail "timeline API returned HTTP $timeline_status"

docker logs --since "$SINCE" "$PLATFORM_CONTAINER" > "$REPORT_DIR/platform.log" 2>&1 || true
if grep -E "Traceback|Exception|ERROR| 500 " "$REPORT_DIR/platform.log" > "$REPORT_DIR/platform_errors.log"; then
  fail "backend errors found; see $REPORT_DIR/platform_errors.log"
fi

echo "[esp32-smoke] PASS report_dir=$REPORT_DIR"
