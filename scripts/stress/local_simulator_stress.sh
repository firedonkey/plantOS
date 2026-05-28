#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8000}"
REPORT_DIR="${REPORT_DIR:-$ROOT_DIR/stress-reports/local-$(date +%Y%m%d-%H%M%S)}"
SCENARIOS="${SCENARIOS:-normal unstable_wifi ota_failure camera_disconnect command_failure reboot_loop low_memory}"
DEVICE_COUNTS="${DEVICE_COUNTS:-1 5 20}"
RUN_SECONDS="${RUN_SECONDS:-15}"
CAMERA_NODES="${CAMERA_NODES:-1}"
START_DOCKER="${START_DOCKER:-1}"
QUEUE_COMMANDS="${QUEUE_COMMANDS:-1}"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-plantlab-local-postgres}"
POSTGRES_USER="${POSTGRES_USER:-plantlab_user}"
POSTGRES_DB="${POSTGRES_DB:-plantlab}"
PLATFORM_CONTAINER="${PLATFORM_CONTAINER:-plantlab-local-platform}"

mkdir -p "$REPORT_DIR"

fail() {
  echo "[stress] ERROR: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

psql_query() {
  docker exec -i "$POSTGRES_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -P pager=off "$@"
}

ensure_docker() {
  if [[ "$START_DOCKER" != "1" ]]; then
    return
  fi
  docker compose -f "$ROOT_DIR/platform/infra/docker/docker-compose.local.yml" up -d --build
}

wait_for_health() {
  for _ in $(seq 1 30); do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done
  fail "local backend health check did not become ready: $BASE_URL/health"
}

detect_device() {
  if [[ -n "${DEVICE_ID:-}" && -n "${DEVICE_TOKEN:-}" ]]; then
    return
  fi
  local row
  row="$(psql_query -Atc "select id || '|' || api_token from devices where api_token is not null order by id limit 1;")"
  [[ -n "$row" ]] || fail "no local device with api_token found; create/provision a local device first"
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

queue_api_command() {
  local token="$1"
  local path="$2"
  local payload="$3"
  curl -fsS \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "$BASE_URL$path" >/dev/null
}

queue_ota_command() {
  local params
  params='{"target_version":"9.9.9","download_url":"/api/hardware/ota/artifacts/sim"}'
  psql_query -c "insert into commands (device_id, target, action, value, status, created_at) values ($DEVICE_ID, 'ota', 'start', '$params', 'pending', now());" >/dev/null
}

queue_commands() {
  [[ "$QUEUE_COMMANDS" == "1" ]] || return
  local token
  token="$(login_token)"
  queue_api_command "$token" "/api/devices/$DEVICE_ID/commands/light" '{"intensity_percent":65}' || true
  queue_api_command "$token" "/api/devices/$DEVICE_ID/commands/capture" '{}' || true
  queue_ota_command || true
}

run_one() {
  local scenario="$1"
  local devices="$2"
  local label="${scenario}-${devices}devices"
  local log_file="$REPORT_DIR/${label}.log"
  echo "[stress] run scenario=$scenario devices=$devices seconds=$RUN_SECONDS"
  local scenario_args=()
  if [[ "$scenario" != "normal" ]]; then
    scenario_args=(--scenario "$scenario")
  else
    scenario_args=(--scenario normal)
  fi

  python3 "$ROOT_DIR/tools/simulator/simulator.py" \
    --base-url "$BASE_URL" \
    --device-id "$DEVICE_ID" \
    --device-token "$DEVICE_TOKEN" \
    --devices "$devices" \
    --camera-nodes "$CAMERA_NODES" \
    "${scenario_args[@]}" \
    --run-seconds "$RUN_SECONDS" \
    --heartbeat-interval 4 \
    --sensor-interval 4 \
    --image-interval 8 \
    --diagnostics-interval 6 \
    --command-poll-interval 2 \
    --ota-step-delay 0.2 \
    --log-level info >"$log_file" 2>&1 &
  local sim_pid=$!
  sleep 3
  queue_commands
  wait "$sim_pid"
  wait_for_health
}

require_cmd curl
require_cmd docker
require_cmd python3

ensure_docker
wait_for_health
detect_device

echo "[stress] report_dir=$REPORT_DIR" | tee "$REPORT_DIR/summary.txt"
echo "[stress] base_url=$BASE_URL device_id=$DEVICE_ID scenarios=[$SCENARIOS] counts=[$DEVICE_COUNTS]" | tee -a "$REPORT_DIR/summary.txt"

for devices in $DEVICE_COUNTS; do
  for scenario in $SCENARIOS; do
    run_one "$scenario" "$devices"
  done
done

SINCE="${SINCE:-60m}" REPORT_DIR="$REPORT_DIR" "$ROOT_DIR/scripts/stress/check_local_health.sh"
echo "[stress] PASS report_dir=$REPORT_DIR"
