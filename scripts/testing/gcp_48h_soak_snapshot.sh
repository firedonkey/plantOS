#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-plantlab-493805}"
DB_HOST="${PLANTLAB_GCP_DB_HOST:-136.112.180.16}"
DB_NAME="${DB_NAME:-plantlab}"
DB_USER="${DB_USER:-plantlab_user}"
DEVICE_ID="${DEVICE_ID:-34}"
MASTER_ID="${MASTER_ID:-pl-esp32-64e0a80af6e8}"
CAMERA_ID="${CAMERA_ID:-pl-cam-1c1df816a398}"
SINCE="${SOAK_STARTED_AT:-2026-05-30T20:37:40Z}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "Missing gcloud." >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "Missing psql." >&2
  exit 1
fi

export PGPASSWORD
PGPASSWORD="$(gcloud secrets versions access latest --secret=db-password --project="${PROJECT_ID}")"

psql "host=${DB_HOST} port=5432 dbname=${DB_NAME} user=${DB_USER} sslmode=require" -P pager=off -v since="${SINCE}" -v device_id="${DEVICE_ID}" -v master_id="${MASTER_ID}" -v camera_id="${CAMERA_ID}" <<'SQL'
\echo === snapshot_time ===
select now() as captured_at, :'since'::timestamptz as soak_started_at;

\echo === nodes ===
select device_id, hardware_device_id, node_role, software_version, status, last_seen_at, ota_status, ota_target_version, ota_error
from device_hardware_ids
where hardware_device_id in (:'master_id', :'camera_id')
order by node_role;

\echo === diagnostic_snapshots ===
select hardware_device_id, node_role, reported_status, firmware_version, uptime_seconds, wifi_rssi_dbm, last_error_code, reported_at, updated_at
from device_diagnostic_snapshots
where hardware_device_id in (:'master_id', :'camera_id')
order by node_role;

\echo === latest_heartbeat_runtime ===
with latest as (
  select distinct on (hardware_device_id)
    hardware_device_id,
    occurred_at,
    metadata
  from device_diagnostic_events
  where event_type='HEARTBEAT_RECEIVED'
    and hardware_device_id in (:'master_id', :'camera_id')
  order by hardware_device_id, occurred_at desc
)
select
  hardware_device_id,
  occurred_at,
  metadata->'data'->>'firmware_version' as firmware_version,
  metadata->'data'->>'uptime_seconds' as uptime_seconds,
  metadata->'data'->>'wifi_rssi_dbm' as wifi_rssi_dbm,
  metadata->'data'->>'free_heap_bytes' as free_heap_bytes,
  metadata->'data'->'runtime'->>'time_sync_status' as time_sync_status,
  metadata->'data'->'runtime'->>'last_ntp_sync_at' as last_ntp_sync_at,
  metadata->'data'->'runtime'->>'ota_status' as runtime_ota_status,
  metadata->'data'->'runtime'->>'camera_node_status' as camera_node_status,
  metadata->'data'->'runtime'->>'last_command_poll_at' as last_command_poll_at,
  metadata->'data'->'runtime'->>'last_command_poll_status' as last_command_poll_status,
  metadata->'data'->'runtime'->>'last_command_poll_error' as last_command_poll_error,
  metadata->'data'->'runtime'->>'last_command_poll_latency_ms' as last_command_poll_latency_ms,
  metadata->'data'->'runtime'->>'command_poll_stale_seconds' as command_poll_stale_seconds
from latest
order by hardware_device_id;

\echo === soak_event_counts ===
select hardware_device_id, event_type, severity, count(*) as event_count, min(occurred_at) as first_at, max(occurred_at) as last_at
from device_diagnostic_events
where device_id = :'device_id'::int
  and occurred_at >= :'since'::timestamptz
group by hardware_device_id, event_type, severity
order by hardware_device_id, event_type, severity;

\echo === soak_image_counts ===
select count(*) as image_count, min(timestamp) as first_image_at, max(timestamp) as latest_image_at
from images
where device_id = :'device_id'::int
  and timestamp >= :'since'::timestamptz;

\echo === soak_command_counts ===
select status, count(*) as command_count, min(created_at) as first_command_at, max(coalesce(completed_at, sent_at, created_at)) as latest_command_at
from commands
where device_id = :'device_id'::int
  and created_at >= :'since'::timestamptz
group by status
order by status;

\echo === recent_non_info_events ===
select id, event_type, severity, hardware_device_id, occurred_at, message
from device_diagnostic_events
where device_id = :'device_id'::int
  and occurred_at >= :'since'::timestamptz
  and severity <> 'info'
order by occurred_at desc
limit 50;
SQL

echo "=== cloud_run_errors_1h ==="
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="plantlab-api" AND severity>=ERROR' \
  --project="${PROJECT_ID}" \
  --freshness=1h \
  --limit=20 \
  --format='table(timestamp,severity,textPayload)' || true
