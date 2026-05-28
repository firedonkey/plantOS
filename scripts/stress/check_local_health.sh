#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8000}"
REPORT_DIR="${REPORT_DIR:-$ROOT_DIR/stress-reports/local-$(date +%Y%m%d-%H%M%S)}"
SINCE="${SINCE:-30m}"
MAX_TOTAL_EVENTS="${MAX_TOTAL_EVENTS:-20000}"
MAX_EVENT_TYPE_COUNT="${MAX_EVENT_TYPE_COUNT:-8000}"

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-plantlab-local-postgres}"
POSTGRES_USER="${POSTGRES_USER:-plantlab_user}"
POSTGRES_DB="${POSTGRES_DB:-plantlab}"
PLATFORM_CONTAINER="${PLATFORM_CONTAINER:-plantlab-local-platform}"

mkdir -p "$REPORT_DIR"

fail() {
  echo "[health] ERROR: $*" >&2
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
  [[ -n "$row" ]] || fail "no local device with api_token found; create/provision a local device first"
  DEVICE_ID="${DEVICE_ID:-${row%%|*}}"
  DEVICE_TOKEN="${DEVICE_TOKEN:-${row#*|}}"
  export DEVICE_ID DEVICE_TOKEN
}

login_token() {
  python3 - "$BASE_URL" <<'PY'
import json
import sys
import urllib.error
import urllib.request

base_url = sys.argv[1].rstrip("/")
payload = json.dumps({"email": "dev@plantlab.local", "password": "password"}).encode()
request = urllib.request.Request(
    f"{base_url}/api/auth/login",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=10) as response:
        print(json.load(response)["token"])
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", "replace")
    raise SystemExit(f"dev login failed: HTTP {exc.code} {body}")
PY
}

require_cmd curl
require_cmd docker
require_cmd python3

docker ps --format '{{.Names}}' | grep -qx "$POSTGRES_CONTAINER" || fail "$POSTGRES_CONTAINER is not running"
docker ps --format '{{.Names}}' | grep -qx "$PLATFORM_CONTAINER" || fail "$PLATFORM_CONTAINER is not running"

echo "[health] checking $BASE_URL/health"
curl -fsS "$BASE_URL/health" | tee "$REPORT_DIR/health.json" >/dev/null

detect_device
echo "[health] using DEVICE_ID=$DEVICE_ID"

TOKEN="$(login_token)"
timeline_status="$(
  curl -sS -o "$REPORT_DIR/timeline.json" -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL/api/devices/$DEVICE_ID/timeline?limit=50"
)"
if [[ "$timeline_status" != "200" ]]; then
  if [[ "$timeline_status" == "404" ]]; then
    fail "timeline API returned HTTP 404; local backend image is likely stale. Rebuild with: docker compose -f platform/infra/docker/docker-compose.local.yml up -d --build"
  fi
  fail "timeline API returned HTTP $timeline_status"
fi
python3 - "$REPORT_DIR/timeline.json" <<'PY'
import json
import sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
events = payload.get("events") or []
if not events:
    raise SystemExit("timeline API returned zero events")
print(f"[health] timeline_events={len(events)}")
PY

psql_query -c "select event_type, count(*) from device_diagnostic_events where occurred_at >= now() - interval '$SINCE' group by event_type order by count desc, event_type;" \
  | tee "$REPORT_DIR/event_counts.txt" >/dev/null

total_events="$(psql_query -Atc "select count(*) from device_diagnostic_events where occurred_at >= now() - interval '$SINCE';")"
max_type_count="$(psql_query -Atc "select coalesce(max(count), 0) from (select count(*) as count from device_diagnostic_events where occurred_at >= now() - interval '$SINCE' group by event_type) counts;")"
echo "[health] recent_total_events=$total_events max_event_type_count=$max_type_count since=$SINCE"
[[ "$total_events" -le "$MAX_TOTAL_EVENTS" ]] || fail "recent event count $total_events exceeds MAX_TOTAL_EVENTS=$MAX_TOTAL_EVENTS"
[[ "$max_type_count" -le "$MAX_EVENT_TYPE_COUNT" ]] || fail "single event type count $max_type_count exceeds MAX_EVENT_TYPE_COUNT=$MAX_EVENT_TYPE_COUNT"

psql_query -c "select event_type, metadata->>'correlation_id' as correlation_id, count(*) from device_diagnostic_events where occurred_at >= now() - interval '$SINCE' and metadata::jsonb ? 'correlation_id' group by event_type, correlation_id having count(*) > 25 order by count desc limit 20;" \
  | tee "$REPORT_DIR/duplicate_candidates.txt" >/dev/null
if grep -Eq '^[[:space:]]*[A-Z_]+[[:space:]]+\|' "$REPORT_DIR/duplicate_candidates.txt"; then
  fail "possible duplicate event storm found; see $REPORT_DIR/duplicate_candidates.txt"
fi

docker logs --since "$SINCE" "$PLATFORM_CONTAINER" > "$REPORT_DIR/platform.log" 2>&1 || true
if grep -E "Traceback|Exception|ERROR| 500 " "$REPORT_DIR/platform.log" > "$REPORT_DIR/platform_errors.log"; then
  fail "backend errors found; see $REPORT_DIR/platform_errors.log"
fi

echo "[health] PASS report_dir=$REPORT_DIR"
