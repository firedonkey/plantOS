# PlantLab Final Clean 48-Hour GCP Soak Report

Status: FAILED / STOPPED

SOAK_STARTED_AT=2026-06-02T22:10:51Z

Expected completion: `2026-06-04T22:10:51Z`

This release-candidate soak failed at the `2026-06-03T09:14:30Z` checkpoint because Cloud Run emitted an ERROR log for `REL-GCP-SOAK-005`. The backend fix was deployed after the soak was stopped, so this run does not count as the release gate. Earlier failed or partial soak runs are archived in `docs/testing/reliability_issues.md` and `docs/testing/gcp_validation_report.md`.

## Baseline

Captured at: `2026-06-02T22:12:22Z`

| Area | Result |
| --- | --- |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Backend health | PASS, `/health` and `/api/health` OK |
| Provisioning health | PASS, `/health` OK |
| Active DB migration | `20260530_0014` |
| DB connection count | `4` `plantlab_user` connections, `1 active`, `3 idle` |
| DB pool settings | `pool_size=2`, `max_overflow=1`, `pool_timeout=10`, `pool_pre_ping=true`, `pool_recycle=1800` |
| Cloud Run scaling | backend max instances `4`, backend concurrency `20`; provisioning max instances `2`, provisioning concurrency `20` |
| Image serving | authenticated proxy endpoint, `PLANTLAB_IMAGE_URL_STRATEGY=proxy` |
| Cloud Run ERROR logs since start | `0` |
| Non-info diagnostics since start | `0` |
| OTA activity since start | none |
| `git diff --check` | PASS |

### Device Baseline

| Device | Firmware | Status | Uptime | RSSI | NTP | Diagnostics |
| --- | --- | --- | ---: | ---: | --- | --- |
| Master `pl-esp32-64e0a80af6e8` | `0.1.6` | online | `190604s` | `-50 dBm` | synchronized | online, no `last_error_code` |
| Camera `pl-cam-1c1df816a398` | `0.1.8` | online | `175546s` | `-61 dBm` | synchronized, `last_ntp_sync_at=2026-05-31T21:26:01Z` | online, no `last_error_code` |

Master command polling baseline:

| Field | Value |
| --- | --- |
| `last_command_poll_at` | `2026-06-02T22:12:16Z` |
| `last_command_poll_status` | `ok` |
| `last_command_poll_latency_ms` | `598` |
| `command_poll_stale_seconds` | `0` |

### Baseline Command And Image Check

| Check | Result |
| --- | --- |
| `REQUEST_DIAGNOSTICS` | Command `314` completed |
| `CAPTURE_IMAGE` | Command `315` completed |
| `SET_LIGHT_BRIGHTNESS` | Command `316` completed |
| Image upload | Image `1606` uploaded at `2026-06-02T22:11:46Z` |
| Image proxy requests | `20/20` authenticated proxy loads passed |
| Command timeouts | `0` |
| `COMMAND_POLL_STALE` | `0` |
| Unexpected OTA events | `0` |

Baseline result: clean. The release-candidate 48-hour soak is active.

## Monitoring Log

Checkpoints are recorded every 30 minutes using:

```bash
SOAK_STARTED_AT=2026-06-02T22:10:51Z scripts/testing/gcp_48h_soak_snapshot.sh
```

### 2026-06-02T22:43:57Z - 30-Minute Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `0h33m06s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `188` |
| Camera heartbeat count | `44` |
| Master uptime | `192483s` |
| Camera uptime | `177436s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-68 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `1173 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `2` |
| Commands since soak start | `3 completed` |
| Command checkpoint | not due; baseline command set already completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `5` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, command polling telemetry stayed healthy, images continued uploading, proxy image access worked, DB connections stayed stable, and no Cloud Run ERROR logs or non-info diagnostics were observed.

### 2026-06-02T23:13:56Z - 1-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `1h03m05s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `361` |
| Camera heartbeat count | `84` |
| Master uptime | `194294s` |
| Camera uptime | `179236s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-60 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `603 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `2` |
| Commands since soak start | `3 completed` |
| Command checkpoint | not due; baseline command set already completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `5` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with uptime progression, command polling stayed current, proxy image access worked, DB usage remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T00:15:09Z - 2-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `2h04m18s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `713` |
| Camera heartbeat count | `166` |
| Master uptime | `197965s` |
| Camera uptime | `182927s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-62 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `679 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `4` |
| Commands since soak start | `6 completed` |
| Command checkpoint | Commands `317`, `318`, `319` completed |
| Capture result | Image `1609` uploaded at `2026-06-03T00:14:36Z` |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `4` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The two-hour authenticated command checkpoint completed successfully, image upload and proxy access worked, both devices remained healthy, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T00:43:56Z - 2.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `2h33m05s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `185` |
| Master uptime | `199694s` |
| Camera uptime | `184637s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `600 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `5` |
| Commands since soak start | `6 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `11` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, scheduled image uploads continued, proxy image access worked, command polling stayed current, DB connections remained within the planned budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T01:13:55Z - 3-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `3h03m04s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `184` |
| Master uptime | `201494s` |
| Camera uptime | `186437s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-60 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `600 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `5` |
| Commands since soak start | `6 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `4` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, image uploads continued, authenticated proxy image access worked, command polling stayed current, DB usage stayed stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T01:43:56Z - 3.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `3h33m05s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `184` |
| Master uptime | `203297s` |
| Camera uptime | `188237s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `604 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `6` |
| Commands since soak start | `6 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `5` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, scheduled image uploads continued, proxy image access worked, command polling stayed current, DB connections stayed stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T02:15:07Z - 4-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `4h04m16s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `777` |
| Camera heartbeat count | `180` |
| Master uptime | `205168s` |
| Camera uptime | `190127s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-60 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `735 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `7` |
| Commands since soak start | `9 completed` |
| Command checkpoint | Commands `320`, `321`, `322` completed |
| Capture result | Image `1612` uploaded at `2026-06-03T02:14:31Z` |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `4` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The four-hour authenticated command checkpoint completed successfully, image upload and proxy access worked, both devices remained healthy, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T02:43:59Z - 4.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `4h33m08s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `183` |
| Master uptime | `206902s` |
| Camera uptime | `191882s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-62 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `708 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `8` |
| Commands since soak start | `9 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `5` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, scheduled image uploads continued, proxy image access worked, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T08:18:03Z - 10-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `10h07m12s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat latest | `2026-06-03T08:18:03Z` |
| Camera heartbeat latest | `2026-06-03T08:17:43Z` |
| Master uptime | `226950s` |
| Camera uptime | `211907s` |
| Master RSSI | `-59 dBm` |
| Camera RSSI | `-65 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `807 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `16` |
| Commands since soak start | `18 completed` |
| Command checkpoint | Commands `329` diagnostics, `330` capture, and `331` light intensity completed |
| Capture result | Image `1621` uploaded at `2026-06-03T08:16:09Z` |
| Image proxy check | Image `1621` loaded via authenticated `/api/images/1621/content` with HTTP `200`, `image/jpeg`, `63558` bytes, `1600x1200` |
| Cloud Run ERROR logs since start | `0` |
| Cloud Run ERROR logs last hour | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle` |
| `COMMAND_POLL_STALE` | `0` |
| Command timeouts | `0` |
| Image upload failures | `0` |
| OTA events | `0` |
| Non-info diagnostics | no active warning; one earlier transient `WIFI_SIGNAL_DEGRADED` remains in event history and recovered after `45s` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 10-hour authenticated command checkpoint completed successfully, image `1621` uploaded and loaded through the authenticated proxy endpoint, both devices remained online with progressing uptime, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, image upload failures, or active non-info diagnostics were observed.

### 2026-06-03T08:44:35Z - 10.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `10h33m44s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat latest | `2026-06-03T08:44:33Z` |
| Camera heartbeat latest | `2026-06-03T08:43:58Z` |
| Master uptime | `228540s` |
| Camera uptime | `213482s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-65 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `597 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `17` |
| Commands since soak start | `18 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | Image `1622` loaded via authenticated `/api/images/1622/content` with HTTP `200`, `image/jpeg`, `63612` bytes, `1600x1200` |
| Cloud Run ERROR logs since start | `0` |
| Cloud Run ERROR logs last hour | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle` |
| `COMMAND_POLL_STALE` | `0` |
| Command timeouts | `0` |
| Image upload failures | `0` |
| OTA events | `0` |
| Non-info diagnostics | `0` recent; no active warning |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, camera NTP stayed synchronized, image uploads continued, image `1622` loaded through the authenticated proxy endpoint, command polling telemetry remained healthy, DB connections stayed stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, image upload failures, or non-info diagnostics were observed.

### 2026-06-03T09:14:30Z - 11-Hour Checkpoint - FAILED

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `11h03m39s` |
| Backend revision | `plantlab-api-00078-mur` |
| Provisioning revision | `plantlab-provision-api-00021-bis` |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat latest | `2026-06-03T09:14:28Z` |
| Camera heartbeat latest | `2026-06-03T09:13:58Z` |
| Master uptime | `230335s` |
| Camera uptime | `215282s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-65 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `610 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `17` |
| Commands since soak start | `18 completed` |
| Cloud Run ERROR logs since start | FAILED: nonzero |
| Cloud Run ERROR detail | `2026-06-03T09:04:13.829437Z` `plantlab-api-00078-mur`, `sqlalchemy.exc.InvalidRequestError: Could not refresh instance '<DeviceDiagnosticEvent ...>'` in `hardware_heartbeat` -> `write_canonical_event` -> `session.refresh(db_event)` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle` |
| `COMMAND_POLL_STALE` | `0` |
| Command timeouts | `0` |
| Image upload failures | `0` image upload failure events |
| OTA events | `0` |
| Non-info diagnostics | FAILED: master `upload_failure` warning, `last_error` error, and `DIAGNOSTICS_RECEIVED` warning at `2026-06-03T09:04:14Z` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: FAILED. This release-candidate soak is stopped because a Cloud Run ERROR log appeared and master non-info diagnostics were emitted. Devices remained online, command polling stayed healthy, commands remained completed, and image uploads continued, but the zero-ERROR release-candidate criterion was violated. Issue documented as `REL-GCP-SOAK-005` in `docs/testing/reliability_issues.md`; no speculative fix was applied during the soak.

### 2026-06-03T15:08:30Z - REL-GCP-SOAK-005 Post-Fix GCP Validation

This validation happened after the release-candidate soak was already stopped. It verifies the backend fix only; it does not revive or count the failed soak.

| Area | Result |
| --- | --- |
| Root cause | `write_canonical_event()` committed a `DeviceDiagnosticEvent` and then crashed the request on post-commit `session.refresh(db_event)` with `sqlalchemy.exc.InvalidRequestError` |
| Fix | Canonical event writer now `flush()`es to capture the event ID, commits the write, then best-effort reloads or returns a detached event if post-commit hydration fails |
| Backend image | `us-central1-docker.pkg.dev/plantlab-493805/plantlab-repo/plantlab-api:7adcb7c-20260603145505` |
| Cloud Run revision | `plantlab-api-00080-hej` at `100%` traffic |
| Health endpoints | PASS, `/health` and `/api/health` OK |
| Commands | `332` diagnostics completed, `333` capture completed, `334` light completed |
| Image upload | Capture command uploaded image `1632` from camera `pl-cam-1c1df816a398` |
| Image proxy | `/api/images/1632/content` returned HTTP `200`, `image/jpeg`, `71505` bytes, `1600x1200` |
| Canonical event writes | Heartbeat, command, image capture, image upload, and command completion events persisted after deploy |
| Cloud Run ERROR logs | `0` for revision `plantlab-api-00080-hej` since `2026-06-03T15:03:00Z` |
| DB connections | `5` `plantlab_user` connections, `3 active`, `2 idle`; total DB connections `17` |
| Post-fix diagnostics | Current master snapshot healthy: `reported_status=online`, firmware `0.1.6`, no `last_error_*`, empty `error_counters` |
| Backend tests | PASS, `.venv/bin/pytest platform/backend/tests -q` with `294 passed` |
| `git diff --check` | PASS after code and documentation updates |

Result: `REL-GCP-SOAK-005` is resolved and deployed. A new clean 48-hour release-candidate soak must be started from a fresh baseline.

### 2026-06-03T07:44:27Z - 9.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `9h33m36s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat latest | `2026-06-03T07:44:21Z` |
| Camera heartbeat latest | `2026-06-03T07:43:58Z` |
| Master uptime | `224927s` |
| Camera uptime | `209882s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-67 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `802 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `15` |
| Commands since soak start | `15 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | not exercised at this checkpoint; image uploads continued and Cloud Run/storage errors stayed `0` |
| Cloud Run ERROR logs since start | `0` |
| Cloud Run ERROR logs last hour | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle` |
| `COMMAND_POLL_STALE` | `0` |
| Command timeouts | `0` |
| Image upload failures | `0` |
| OTA events | `0` |
| Non-info diagnostics | no active warning; one earlier transient `WIFI_SIGNAL_DEGRADED` remains in event history and recovered after `45s` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: monitoring continues. Master and camera remained online with current heartbeats and progressing uptime, camera NTP stayed synchronized, command polling telemetry remained healthy, image uploads continued, DB connections remained stable, and there were no command timeouts, `COMMAND_POLL_STALE` events, image upload failures, OTA events, Cloud Run ERROR logs, or DB connection errors. The only non-info event visible since soak start remains the earlier recovered camera Wi-Fi RSSI dip.

### 2026-06-03T07:14:25Z - 9-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `9h03m34s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat latest | `2026-06-03T07:14:24Z` |
| Camera heartbeat latest | `2026-06-03T07:13:58Z` |
| Master uptime | `223131s` |
| Camera uptime | `208082s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-67 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `605 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `14` |
| Commands since soak start | `15 completed` |
| Command checkpoint | not due; previous command set completed |
| Cloud Run ERROR logs since start | `0` |
| Cloud Run ERROR logs last hour | `0` |
| DB PlantLab connections | `3` |
| `COMMAND_POLL_STALE` | `0` |
| Command timeouts | `0` |
| Image upload failures | `0` |
| OTA events | `0` |
| Non-info diagnostics | no active warning; one earlier transient `WIFI_SIGNAL_DEGRADED` remains in event history and recovered after `45s` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: monitoring continues. Master and camera remained online with current heartbeats and progressing uptime, camera NTP stayed synchronized, command polling telemetry remained healthy, and there were no command timeouts, `COMMAND_POLL_STALE` events, image upload failures, OTA events, Cloud Run ERROR logs, or DB connection errors. The only non-info event visible since soak start remains the earlier recovered camera Wi-Fi RSSI dip.

### 2026-06-03T06:15:59Z - 8-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `8h05m08s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `780` |
| Camera heartbeat count | `177` |
| Master uptime | `219622s` |
| Camera uptime | `204572s` |
| Master RSSI | `-58 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `812 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `13` |
| Commands since soak start | `15 completed` |
| Command checkpoint | Commands `326`, `327`, `328` completed |
| Capture result | Image `1618` uploaded at `2026-06-03T06:15:14Z` |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `6` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The eight-hour authenticated command checkpoint completed successfully, image upload and proxy access worked, both devices remained healthy, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T06:44:31Z - 8.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `8h33m40s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `180` |
| Master uptime | `221335s` |
| Camera uptime | `206282s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-65 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `811 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `14` |
| Commands since soak start | `15 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `5` |
| Non-info diagnostics | one transient `WIFI_SIGNAL_DEGRADED`, recovered after `45s` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: monitoring continues. The camera reported `WIFI_SIGNAL_DEGRADED` at `2026-06-03T06:24:28Z` and `WIFI_SIGNAL_RECOVERED` at `2026-06-03T06:25:13Z`; heartbeats continued through the event, the camera remained online, diagnostics returned to healthy, image uploads continued, and Cloud Run ERROR logs stayed `0`. This was transient and is not classified as a blocker unless warnings persist or recur.

### 2026-06-03T05:44:30Z - 7.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `7h33m39s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `182` |
| Master uptime | `217735s` |
| Camera uptime | `202682s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `606 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `12` |
| Commands since soak start | `12 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `5` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, scheduled image uploads continued, proxy image access worked, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T04:15:00Z - 6-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `6h04m09s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `780` |
| Camera heartbeat count | `177` |
| Master uptime | `212359s` |
| Camera uptime | `197327s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-64 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `705 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `10` |
| Commands since soak start | `12 completed` |
| Command checkpoint | Commands `323`, `324`, `325` completed |
| Capture result | Image `1615` uploaded at `2026-06-03T04:14:30Z` |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `10` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The six-hour authenticated command checkpoint completed successfully, image upload and proxy access worked, both devices remained healthy, command polling stayed current, DB connections remained within the planned budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T04:44:28Z - 6.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `6h33m37s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `796` |
| Camera heartbeat count | `180` |
| Master uptime | `214127s` |
| Camera uptime | `199082s` |
| Master RSSI | `-56 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `597 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `11` |
| Commands since soak start | `12 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `5` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, scheduled image uploads continued, proxy image access worked, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T03:13:56Z - 5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `5h03m05s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `796` |
| Camera heartbeat count | `180` |
| Master uptime | `208700s` |
| Camera uptime | `193637s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-61 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `603 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `8` |
| Commands since soak start | `9 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `5` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, proxy image access worked, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-03T03:43:57Z - 5.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `5h33m06s` |
| Backend revision | `plantlab-api-00078-mur` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `797` |
| Camera heartbeat count | `179` |
| Master uptime | `210501s` |
| Camera uptime | `195437s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `717 ms` |
| `command_poll_stale_seconds` | `0` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-05-31T21:26:01Z` |
| Images uploaded since soak start | `9` |
| Commands since soak start | `9 completed` |
| Command checkpoint | not due; previous command set completed |
| Image proxy check | `10/10` authenticated loads passed |
| Cloud Run ERROR logs | `0` |
| DB PlantLab connections | `4` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with progressing uptime, scheduled image uploads continued, proxy image access worked, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.
