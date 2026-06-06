# PlantLab Final Clean 48-Hour GCP Soak Report

Status: PASSED

SOAK_STARTED_AT=2026-06-04T04:29:20Z

Expected completion: `2026-06-06T04:29:20Z`

Completed at: `2026-06-06T04:34:55Z`

Final result: clean 48-hour release-candidate GCP soak passed. PlantLab is ready for private beta from this soak gate.

This is a fresh release-candidate soak after the prior run was interrupted by an accidental manual master reset. That interruption is documented as `REL-GCP-SOAK-006` and is not classified as a product reliability failure. Previous failed, interrupted, or partial soak runs are archived in `docs/testing/reliability_issues.md` and `docs/testing/gcp_validation_report.md`.

Committed baseline:

- Commit `6c62cd7` (`Harden GCP reliability soak paths`) was pushed to `origin/main` before this soak series started.
- The soak report should remain uncommitted until the soak completes unless a blocker requires a fix.

## Baseline

Captured at: `2026-06-04T04:30:33Z`

| Area | Result |
| --- | --- |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Backend health | PASS, `/health` and `/api/health` OK |
| Provisioning health | PASS, `/health` OK |
| Active DB migration | `20260530_0014` |
| DB connection count | `5` `plantlab_user` connections, `1 active`, `4 idle`; `17` total |
| DB pool settings | `pool_size=2`, `max_overflow=1`, `pool_timeout=10`, `pool_pre_ping=true`, `pool_recycle=1800` |
| Cloud Run scaling | backend max instances `4`, backend concurrency `20`; provisioning max instances `2`, provisioning concurrency `20` |
| Image serving | authenticated proxy endpoint, `PLANTLAB_IMAGE_URL_STRATEGY=proxy` |
| Cloud Run ERROR logs since start | `0` |
| Non-info diagnostics since start | `0` |
| OTA activity since start | none |
| `git diff --check` | PASS after report rewrite |

### Device Baseline

| Device | Firmware | Status | Uptime | RSSI | NTP | Diagnostics |
| --- | --- | --- | ---: | ---: | --- | --- |
| Master `pl-esp32-64e0a80af6e8` | `0.1.6` | online | `439s` | `-48 dBm` | synchronized, `last_ntp_sync_at=2026-06-04T04:23:22Z` | online, no `last_error_code` |
| Camera `pl-cam-1c1df816a398` | `0.1.8` | online | `49233s` | `-57 dBm` | synchronized, `last_ntp_sync_at=2026-06-03T14:49:57Z` | online, no `last_error_code` |

Master command polling baseline:

| Field | Value |
| --- | --- |
| `last_command_poll_at` | `2026-06-04T04:30:28Z` |
| `last_command_poll_status` | `ok` |
| `last_command_poll_error` | empty |
| `last_command_poll_latency_ms` | `596` |
| `command_poll_stale_seconds` | `0` |

## Start Validation

Initial command checkpoint:

| Command | Result |
| --- | --- |
| `341` diagnostics request | completed, `diagnostics heartbeat sent` |
| `342` camera capture | completed, `camera uploaded a new image` |
| `343` light set intensity `50` | completed, `growing light intensity set to 50%` |

Initial image validation:

| Image | Result |
| --- | --- |
| `1653` | uploaded at `2026-06-04T04:30:08Z` from camera `pl-cam-1c1df816a398` |
| Proxy check | `/api/images/1653/content` returned HTTP `200`, `image/jpeg`, `73647` bytes, `1600x1200` |

Initial event summary since start:

| Area | Result |
| --- | --- |
| Master heartbeats | `9`, latest `2026-06-04T04:30:29Z` |
| Camera heartbeats | `2`, latest `2026-06-04T04:30:23Z` |
| Commands | `3 completed`, `0 timed_out` |
| Images | `1 uploaded`, `0 failures` |
| Command polling | healthy, no `COMMAND_POLL_STALE` |
| Diagnostics | no non-info events |
| OTA | no retry, failure, or unexpected OTA events |
| Cloud Run | no ERROR logs for backend or provisioning since start |

Result: clean start. The final clean 48-hour release-candidate GCP soak is active.

### 2026-06-04T05:02:27Z - 30-Minute Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `0h33m07s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `195` |
| Camera heartbeat count | `44` |
| Master heartbeat latest | `2026-06-04T05:02:25Z` |
| Camera heartbeat latest | `2026-06-04T05:01:54Z` |
| Master uptime | `2355s` |
| Camera uptime | `51123s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `638 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `1` |
| Latest image proxy check | image `1653` HTTP `200`, `image/jpeg`, `73647` bytes, `1600x1200` |
| Commands since soak start | `3 completed`, `0 timed_out` |
| Command checkpoint | not due; initial command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, master command polling stayed current, image `1653` loaded through the authenticated proxy, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T05:32:25Z - 1-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `1h03m05s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `368` |
| Camera heartbeat count | `84` |
| Master heartbeat latest | `2026-06-04T05:32:25Z` |
| Camera heartbeat latest | `2026-06-04T05:31:53Z` |
| Master uptime | `4154s` |
| Camera uptime | `52923s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-52 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `595 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `2` |
| Latest image proxy check | image `1654` HTTP `200`, `image/jpeg`, `62841` bytes, `1600x1200` |
| Commands since soak start | `3 completed`, `0 timed_out` |
| Command checkpoint | not due; initial command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, image uploads continued, image `1654` loaded through the authenticated proxy, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T06:02:27Z - 1.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `1h33m07s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `543` |
| Camera heartbeat count | `124` |
| Master heartbeat latest | `2026-06-04T06:02:24Z` |
| Camera heartbeat latest | `2026-06-04T06:01:53Z` |
| Master uptime | `5954s` |
| Camera uptime | `54723s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `892 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `2` |
| Latest image proxy check | image `1654` HTTP `200`, `image/jpeg`, `62841` bytes, `1600x1200` |
| Commands since soak start | `3 completed`, `0 timed_out` |
| Command checkpoint | not due; initial command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T06:32:31Z - 2-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `2h03m11s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `718` |
| Camera heartbeat count | `164` |
| Master heartbeat latest | `2026-06-04T06:32:24Z` |
| Camera heartbeat latest | `2026-06-04T06:31:53Z` |
| Master uptime | `7753s` |
| Camera uptime | `56524s` |
| Master RSSI | `-54 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `602 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `4` |
| Latest image proxy check | image `1656` HTTP `200`, `image/jpeg`, `61605` bytes, `1600x1200` |
| Commands since soak start | `6 completed`, `0 timed_out` |
| Command checkpoint | commands `344`, `345`, and `346` completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `3 active`, `2 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 2-hour command checkpoint passed: diagnostics, capture, and light commands completed, capture produced image `1656`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T07:02:49Z - 2.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `2h33m29s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-04T07:02:43Z` |
| Camera heartbeat latest | `2026-06-04T07:02:39Z` |
| Master uptime | `9573s` |
| Camera uptime | `58369s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-64 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `1177 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `4` |
| Latest image proxy check | image `1656` HTTP `200`, `image/jpeg`, `61605` bytes, `1600x1200` |
| Commands since soak start | `6 completed`, `0 timed_out` |
| Command checkpoint | not due; 2-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T07:32:58Z - 3-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `3h03m38s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T07:32:49Z` |
| Camera heartbeat latest | `2026-06-04T07:32:38Z` |
| Master uptime | `11379s` |
| Camera uptime | `60169s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `913 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `5` |
| Latest image proxy check | image `1657` HTTP `200`, `image/jpeg`, `60556` bytes, `1600x1200` |
| Commands since soak start | `6 completed`, `0 timed_out` |
| Command checkpoint | not due; 2-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `7` total, `1 active`, `6 idle`; `19` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for the latest upload, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T08:02:57Z - 3.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `3h33m37s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T08:02:52Z` |
| Camera heartbeat latest | `2026-06-04T08:02:38Z` |
| Master uptime | `13182s` |
| Camera uptime | `61969s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `801 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `5` |
| Latest image proxy check | image `1657` HTTP `200`, `image/jpeg`, `60556` bytes, `1600x1200` |
| Commands since soak start | `6 completed`, `0 timed_out` |
| Command checkpoint | not due; 2-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `6` total, `2 active`, `4 idle`; `18` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for the latest upload, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T08:34:30Z - 4-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `4h05m10s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `775` |
| Camera heartbeat count | `176` |
| Master heartbeat latest | `2026-06-04T08:34:19Z` |
| Camera heartbeat latest | `2026-06-04T08:34:09Z` |
| Master uptime | `15069s` |
| Camera uptime | `63859s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-60 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `596 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `7` |
| Latest image proxy check | image `1659` HTTP `200`, `image/jpeg`, `61700` bytes, `1600x1200` |
| Commands since soak start | `9 completed`, `0 timed_out` |
| Command checkpoint | commands `347`, `348`, and `349` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `18` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 4-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1659`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T09:02:53Z - 4.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `4h33m33s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T09:02:51Z` |
| Camera heartbeat latest | `2026-06-04T09:02:38Z` |
| Master uptime | `16781s` |
| Camera uptime | `65569s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `597 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `7` |
| Latest image proxy check | image `1659` HTTP `200`, `image/jpeg`, `61700` bytes, `1600x1200` |
| Commands since soak start | `9 completed`, `0 timed_out` |
| Command checkpoint | not due; 4-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `6` total, `4 active`, `2 idle`; `18` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for the latest upload, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T09:32:58Z - 5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `5h03m38s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T09:32:56Z` |
| Camera heartbeat latest | `2026-06-04T09:32:39Z` |
| Master uptime | `18586s` |
| Camera uptime | `67369s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `605 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `8` |
| Latest image proxy check | image `1660` HTTP `200`, `image/jpeg`, `61906` bytes, `1600x1200` |
| Commands since soak start | `9 completed`, `0 timed_out` |
| Command checkpoint | not due; 4-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `8` total, `4 active`, `4 idle`; `20` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, scheduled image upload continued with image `1660`, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T10:03:01Z - 5.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `5h33m41s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T10:02:59Z` |
| Camera heartbeat latest | `2026-06-04T10:02:38Z` |
| Master uptime | `20389s` |
| Camera uptime | `69169s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `591 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `8` |
| Latest image proxy check | image `1660` HTTP `200`, `image/jpeg`, `61906` bytes, `1600x1200` |
| Commands since soak start | `9 completed`, `0 timed_out` |
| Command checkpoint | not due; 4-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1660`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T10:34:16Z - 6-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `6h04m56s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `773` |
| Camera heartbeat count | `177` |
| Master heartbeat latest | `2026-06-04T10:34:16Z` |
| Camera heartbeat latest | `2026-06-04T10:34:09Z` |
| Master uptime | `22266s` |
| Camera uptime | `71059s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `603 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `10` |
| Latest image proxy check | image `1662` HTTP `200`, `image/jpeg`, `62021` bytes, `1600x1200` |
| Commands since soak start | `12 completed`, `0 timed_out` |
| Command checkpoint | commands `350`, `351`, and `352` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `6` total, `1 active`, `5 idle`; `18` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 6-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1662`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T11:02:58Z - 6.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `6h33m38s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T11:02:48Z` |
| Camera heartbeat latest | `2026-06-04T11:02:38Z` |
| Master uptime | `23977s` |
| Camera uptime | `72769s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-56 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `600 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `10` |
| Latest image proxy check | image `1662` HTTP `200`, `image/jpeg`, `62021` bytes, `1600x1200` |
| Commands since soak start | `12 completed`, `0 timed_out` |
| Command checkpoint | not due; 6-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `7` total, `3 active`, `4 idle`; `19` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1662`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T11:33:00Z - 7-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `7h03m40s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-04T11:32:58Z` |
| Camera heartbeat latest | `2026-06-04T11:32:38Z` |
| Master uptime | `25787s` |
| Camera uptime | `74569s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `909 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `11` |
| Latest image proxy check | image `1663` HTTP `200`, `image/jpeg`, `62043` bytes, `1600x1200` |
| Commands since soak start | `12 completed`, `0 timed_out` |
| Command checkpoint | not due; 6-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `8` total, `3 active`, `5 idle`; `21` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, scheduled image upload continued with image `1663`, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T12:02:58Z - 7.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `7h33m38s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T12:02:50Z` |
| Camera heartbeat latest | `2026-06-04T12:02:39Z` |
| Master uptime | `27579s` |
| Camera uptime | `76369s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-56 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `694 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `11` |
| Latest image proxy check | image `1663` HTTP `200`, `image/jpeg`, `62043` bytes, `1600x1200` |
| Commands since soak start | `12 completed`, `0 timed_out` |
| Command checkpoint | not due; 6-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `7` total, `3 active`, `4 idle`; `19` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1663`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T12:34:11Z - 8-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `8h04m51s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `771` |
| Camera heartbeat count | `176` |
| Master heartbeat latest | `2026-06-04T12:34:03Z` |
| Camera heartbeat latest | `2026-06-04T12:34:09Z` |
| Master uptime | `29453s` |
| Camera uptime | `78259s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `596 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `14` |
| Latest image proxy check | image `1666` HTTP `200`, `image/jpeg`, `61970` bytes, `1600x1200` |
| Commands since soak start | `15 completed`, `0 timed_out` |
| Command checkpoint | commands `353`, `354`, and `355` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `6` total, `1 active`, `5 idle`; `18` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 8-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1666`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T13:02:57Z - 8.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `8h33m37s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-04T13:02:47Z` |
| Camera heartbeat latest | `2026-06-04T13:02:38Z` |
| Master uptime | `31177s` |
| Camera uptime | `79969s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-60 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `545 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `14` |
| Latest image proxy check | image `1666` HTTP `200`, `image/jpeg`, `61970` bytes, `1600x1200` |
| Commands since soak start | `15 completed`, `0 timed_out` |
| Command checkpoint | not due; 8-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `6` total, `3 active`, `3 idle`; `18` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1666`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T13:32:54Z - 9-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `9h03m34s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `178` |
| Master heartbeat latest | `2026-06-04T13:32:53Z` |
| Camera heartbeat latest | `2026-06-04T13:32:39Z` |
| Master uptime | `32983s` |
| Camera uptime | `81769s` |
| Master RSSI | `-45 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `607 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `15` |
| Latest image proxy check | image `1667` HTTP `200`, `image/jpeg`, `61732` bytes, `1600x1200` |
| Commands since soak start | `15 completed`, `0 timed_out` |
| Command checkpoint | not due; 8-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `7` total, `1 active`, `6 idle`; `19` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, scheduled image upload continued with image `1667`, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T14:03:01Z - 9.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `9h33m41s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-04T14:02:59Z` |
| Camera heartbeat latest | `2026-06-04T14:02:39Z` |
| Master uptime | `34789s` |
| Camera uptime | `83569s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `596 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `15` |
| Latest image proxy check | image `1667` HTTP `200`, `image/jpeg`, `61732` bytes, `1600x1200` |
| Commands since soak start | `15 completed`, `0 timed_out` |
| Command checkpoint | not due; 8-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `7` total, `3 active`, `4 idle`; `19` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1667`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T14:34:15Z - 10-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `10h04m55s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `772` |
| Camera heartbeat count | `175` |
| Master heartbeat latest | `2026-06-04T14:34:12Z` |
| Camera heartbeat latest | `2026-06-04T14:34:09Z` |
| Master uptime | `36662s` |
| Camera uptime | `85459s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-53 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `599 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `17` |
| Latest image proxy check | image `1669` HTTP `200`, `image/jpeg`, `64153` bytes, `1600x1200` |
| Commands since soak start | `18 completed`, `0 timed_out` |
| Command checkpoint | commands `356`, `357`, and `358` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `6` total, `3 active`, `3 idle`; `18` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 10-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1669`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T15:02:58Z - 10.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `10h33m38s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-04T15:02:52Z` |
| Camera heartbeat latest | `2026-06-04T15:02:39Z` |
| Master uptime | `38381s` |
| Camera uptime | `87169s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-53 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `596 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `17` |
| Latest image proxy check | image `1669` HTTP `200`, `image/jpeg`, `64153` bytes, `1600x1200` |
| Commands since soak start | `18 completed`, `0 timed_out` |
| Command checkpoint | not due; 10-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `2 active`, `3 idle`; `20` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1669`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T15:33:02Z - 11-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `11h03m42s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-04T15:32:53Z` |
| Camera heartbeat latest | `2026-06-04T15:32:39Z` |
| Master uptime | `40182s` |
| Camera uptime | `88969s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-67 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `606 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `18` |
| Latest image proxy check | image `1670` HTTP `200`, `image/jpeg`, `66760` bytes, `1600x1200` |
| Commands since soak start | `18 completed`, `0 timed_out` |
| Command checkpoint | not due; 10-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `7` total, `3 active`, `4 idle`; `19` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, scheduled image upload continued with image `1670`, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T16:02:59Z - 11.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `11h33m39s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-04T16:02:50Z` |
| Camera heartbeat latest | `2026-06-04T16:02:39Z` |
| Master uptime | `41980s` |
| Camera uptime | `90769s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-71 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `600 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `18` |
| Latest image proxy check | image `1670` HTTP `200`, `image/jpeg`, `66760` bytes, `1600x1200` |
| Commands since soak start | `18 completed`, `0 timed_out` |
| Command checkpoint | not due; 10-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `6` total, `2 active`, `4 idle`; `18` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1670`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T16:34:12Z - 12-Hour Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `12h04m52s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `773` |
| Camera heartbeat count | `177` |
| Master heartbeat latest | `2026-06-04T16:34:05Z` |
| Camera heartbeat latest | `2026-06-04T16:34:09Z` |
| Master uptime | `43855s` |
| Camera uptime | `92659s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-70 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `599 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `20` |
| Latest image proxy check | image `1672` HTTP `200`, `image/jpeg`, `66644` bytes, `1600x1200` |
| Commands since soak start | `21 completed`, `0 timed_out` |
| Command checkpoint | commands `359`, `360`, and `361` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 12-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1672`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T17:02:49Z - 12.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `12h33m29s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-04T17:02:49Z` |
| Camera heartbeat latest | `2026-06-04T17:02:39Z` |
| Master uptime | `45578s` |
| Camera uptime | `94369s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-68 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `598 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `20` |
| Latest image proxy check | image `1672` HTTP `200`, `image/jpeg`, `66644` bytes, `1600x1200` |
| Commands since soak start | `21 completed`, `0 timed_out` |
| Command checkpoint | not due; 12-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1672`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T17:32:52Z - 13-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `13h03m32s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T17:32:43Z` |
| Camera heartbeat latest | `2026-06-04T17:32:39Z` |
| Master uptime | `47373s` |
| Camera uptime | `96169s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-66 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `609 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `21` |
| Latest image proxy check | image `1673` HTTP `200`, `image/jpeg`, `66252` bytes, `1600x1200` |
| Commands since soak start | `21 completed`, `0 timed_out` |
| Command checkpoint | not due; 12-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, scheduled image upload continued with image `1673`, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T18:02:50Z - 13.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `13h33m30s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-04T18:02:48Z` |
| Camera heartbeat latest | `2026-06-04T18:02:39Z` |
| Master uptime | `49177s` |
| Camera uptime | `97969s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-68 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `588 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `21` |
| Latest image proxy check | image `1673` HTTP `200`, `image/jpeg`, `66252` bytes, `1600x1200` |
| Commands since soak start | `21 completed`, `0 timed_out` |
| Command checkpoint | not due; 12-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1673`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T18:33:36Z - 14-Hour Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `14h04m16s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `773` |
| Camera heartbeat count | `177` |
| Master heartbeat latest | `2026-06-04T18:33:28Z` |
| Camera heartbeat latest | `2026-06-04T18:33:24Z` |
| Master uptime | `51017s` |
| Camera uptime | `99814s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-66 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `652 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `23` |
| Latest image proxy check | image `1675` HTTP `200`, `image/jpeg`, `65904` bytes, `1600x1200` |
| Commands since soak start | `24 completed`, `0 timed_out` |
| Command checkpoint | commands `362`, `363`, and `364` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 14-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1675`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T19:02:50Z - 14.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `14h33m30s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-04T19:02:45Z` |
| Camera heartbeat latest | `2026-06-04T19:02:39Z` |
| Master uptime | `52774s` |
| Camera uptime | `101569s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-66 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `601 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `23` |
| Latest image proxy check | image `1675` HTTP `200`, `image/jpeg`, `65904` bytes, `1600x1200` |
| Commands since soak start | `24 completed`, `0 timed_out` |
| Command checkpoint | not due; 14-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1675`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T19:32:49Z - 15-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `15h03m29s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `787` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T19:32:44Z` |
| Camera heartbeat latest | `2026-06-04T19:32:39Z` |
| Master uptime | `54573s` |
| Camera uptime | `103369s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-66 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `597 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `25` |
| Latest image proxy check | image `1677` HTTP `200`, `image/jpeg`, `65530` bytes, `1600x1200` |
| Commands since soak start | `24 completed`, `0 timed_out` |
| Command checkpoint | not due; 14-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, scheduled image upload continued with image `1677`, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T20:02:54Z - 15.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `15h33m34s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T20:02:50Z` |
| Camera heartbeat latest | `2026-06-04T20:02:39Z` |
| Master uptime | `56380s` |
| Camera uptime | `105169s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-65 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `604 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `25` |
| Latest image proxy check | image `1677` HTTP `200`, `image/jpeg`, `65530` bytes, `1600x1200` |
| Commands since soak start | `24 completed`, `0 timed_out` |
| Command checkpoint | not due; 14-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1677`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T20:33:35Z - 16-Hour Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `16h04m15s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `769` |
| Camera heartbeat count | `177` |
| Master heartbeat latest | `2026-06-04T20:33:25Z` |
| Camera heartbeat latest | `2026-06-04T20:33:24Z` |
| Master uptime | `58214s` |
| Camera uptime | `107014s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-63 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `657 ms` |
| `command_poll_stale_seconds` | `1` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `27` |
| Latest image proxy check | image `1679` HTTP `200`, `image/jpeg`, `64707` bytes, `1600x1200` |
| Commands since soak start | `27 completed`, `0 timed_out` |
| Command checkpoint | commands `365`, `366`, and `367` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 16-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1679`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T21:02:50Z - 16.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `16h33m30s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T21:02:45Z` |
| Camera heartbeat latest | `2026-06-04T21:02:39Z` |
| Master uptime | `59975s` |
| Camera uptime | `108769s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-63 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `594 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `27` |
| Latest image proxy check | image `1679` HTTP `200`, `image/jpeg`, `64707` bytes, `1600x1200` |
| Commands since soak start | `27 completed`, `0 timed_out` |
| Command checkpoint | not due; 16-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1679`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T21:32:50Z - 17-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `17h03m30s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `787` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-04T21:32:41Z` |
| Camera heartbeat latest | `2026-06-04T21:32:39Z` |
| Master uptime | `61770s` |
| Camera uptime | `110569s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-61 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `593 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `28` |
| Latest image proxy check | image `1680` HTTP `200`, `image/jpeg`, `64113` bytes, `1600x1200` |
| Commands since soak start | `27 completed`, `0 timed_out` |
| Command checkpoint | not due; 16-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, scheduled image upload continued with image `1680`, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T22:02:50Z - 17.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `17h33m30s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-04T22:02:43Z` |
| Camera heartbeat latest | `2026-06-04T22:02:39Z` |
| Master uptime | `63573s` |
| Camera uptime | `112369s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-63 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `601 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `28` |
| Latest image proxy check | image `1680` HTTP `200`, `image/jpeg`, `64113` bytes, `1600x1200` |
| Commands since soak start | `27 completed`, `0 timed_out` |
| Command checkpoint | not due; 16-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1680`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T22:33:42Z - 18-Hour Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `18h04m22s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `772` |
| Camera heartbeat count | `177` |
| Master heartbeat latest | `2026-06-04T22:33:34Z` |
| Camera heartbeat latest | `2026-06-04T22:33:25Z` |
| Master uptime | `65423s` |
| Camera uptime | `114216s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-61 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `661 ms` |
| `command_poll_stale_seconds` | `1` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `30` |
| Latest image proxy check | image `1682` HTTP `200`, `image/jpeg`, `64441` bytes, `1600x1200` |
| Commands since soak start | `30 completed`, `0 timed_out` |
| Command checkpoint | commands `368`, `369`, and `370` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 18-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1682`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T23:02:51Z - 18.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `18h33m31s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-04T23:02:48Z` |
| Camera heartbeat latest | `2026-06-04T23:02:40Z` |
| Master uptime | `67177s` |
| Camera uptime | `115971s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-62 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `605 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `30` |
| Latest image proxy check | image `1682` HTTP `200`, `image/jpeg`, `64441` bytes, `1600x1200` |
| Commands since soak start | `30 completed`, `0 timed_out` |
| Command checkpoint | not due; 18-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1682`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-04T23:32:51Z - 19-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `19h03m31s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `787` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-04T23:32:43Z` |
| Camera heartbeat latest | `2026-06-04T23:32:40Z` |
| Master uptime | `68973s` |
| Camera uptime | `117771s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `607 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `32` |
| Latest image proxy check | image `1684` HTTP `200`, `image/jpeg`, `64457` bytes, `1600x1200` |
| Commands since soak start | `30 completed`, `0 timed_out` |
| Command checkpoint | not due; 18-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, scheduled image upload continued with image `1684`, authenticated image proxy access worked, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T00:02:53Z - 19.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `19h33m33s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `789` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T00:02:49Z` |
| Camera heartbeat latest | `2026-06-05T00:02:40Z` |
| Master uptime | `70779s` |
| Camera uptime | `119571s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-69 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `597 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `32` |
| Latest image proxy check | image `1684` HTTP `200`, `image/jpeg`, `64457` bytes, `1600x1200` |
| Commands since soak start | `30 completed`, `0 timed_out` |
| Command checkpoint | not due; 18-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, authenticated image proxy access worked for image `1684`, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T00:33:41Z - 20-Hour Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `20h04m21s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `770` |
| Camera heartbeat count | `176` |
| Master heartbeat latest | `2026-06-05T00:33:41Z` |
| Camera heartbeat latest | `2026-06-05T00:33:25Z` |
| Master uptime | `72630s` |
| Camera uptime | `121416s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-68 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `581 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `34` |
| Latest image proxy check | image `1686` HTTP `200`, `image/jpeg`, `64832` bytes, `1600x1200` |
| Commands since soak start | `33 completed`, `0 timed_out` |
| Command checkpoint | commands `371`, `372`, and `373` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `2 active`, `2 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 20-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1686`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T01:02:52Z - 20.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `20h33m32s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T01:02:43Z` |
| Camera heartbeat latest | `2026-06-05T01:02:40Z` |
| Master uptime | `74373s` |
| Camera uptime | `123171s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-72 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `782 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `34` |
| Latest image proxy check | image `1686` HTTP `200`, `image/jpeg`, `64832` bytes, `1600x1200` |
| Commands since soak start | `33 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 22-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, authenticated image proxy returned HTTP `200`, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T01:32:54Z - 21-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `21h03m34s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `787` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T01:32:48Z` |
| Camera heartbeat latest | `2026-06-05T01:32:40Z` |
| Master uptime | `76177s` |
| Camera uptime | `124971s` |
| Master RSSI | `-54 dBm` |
| Camera RSSI | `-60 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `897 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `35` |
| Latest image proxy check | image `1687` HTTP `200`, `image/jpeg`, `69439` bytes, `1600x1200` |
| Commands since soak start | `33 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 22-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, image uploads advanced to image `1687`, authenticated image proxy returned HTTP `200`, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T02:02:51Z - 21.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `21h33m31s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-05T02:02:44Z` |
| Camera heartbeat latest | `2026-06-05T02:02:40Z` |
| Master uptime | `77974s` |
| Camera uptime | `126771s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-61 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `732 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `35` |
| Latest image proxy check | image `1687` HTTP `200`, `image/jpeg`, `69439` bytes, `1600x1200` |
| Commands since soak start | `33 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 22-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `2 active`, `3 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, latest authenticated image proxy returned HTTP `200`, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T02:34:27Z - 22-Hour Command Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `22h05m07s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `773` |
| Camera heartbeat count | `177` |
| Master heartbeat latest | `2026-06-05T02:34:19Z` |
| Camera heartbeat latest | `2026-06-05T02:34:10Z` |
| Master uptime | `79868s` |
| Camera uptime | `128661s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-62 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `815 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `37` |
| Latest image proxy check | image `1689` HTTP `200`, `image/jpeg`, `65877` bytes, `1600x1200` |
| Commands since soak start | `36 completed`, `0 timed_out` |
| Command checkpoint | commands `374`, `375`, and `376` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 22-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1689`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T03:02:53Z - 22.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `22h33m33s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-05T03:02:50Z` |
| Camera heartbeat latest | `2026-06-05T03:02:40Z` |
| Master uptime | `81580s` |
| Camera uptime | `130371s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `589 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `37` |
| Latest image proxy check | image `1689` HTTP `200`, `image/jpeg`, `65877` bytes, `1600x1200` |
| Commands since soak start | `36 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 24-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle`; `15` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, latest authenticated image proxy returned HTTP `200`, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T03:33:00Z - 23-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `23h03m40s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T03:32:59Z` |
| Camera heartbeat latest | `2026-06-05T03:32:40Z` |
| Master uptime | `83389s` |
| Camera uptime | `132171s` |
| Master RSSI | `-57 dBm` |
| Camera RSSI | `-55 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `809 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `38` |
| Latest image proxy check | image `1690` HTTP `200`, `image/jpeg`, `63159` bytes, `1600x1200` |
| Commands since soak start | `36 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 24-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, image uploads advanced to image `1690`, authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T04:03:03Z - 23.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `23h33m43s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-05T04:02:56Z` |
| Camera heartbeat latest | `2026-06-05T04:02:40Z` |
| Master uptime | `85186s` |
| Camera uptime | `133971s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-53 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `601 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `38` |
| Latest image proxy check | image `1690` HTTP `200`, `image/jpeg`, `63159` bytes, `1600x1200` |
| Commands since soak start | `36 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 24-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, latest authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T04:33:44Z - 24-Hour Command Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `24h04m24s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `774` |
| Camera heartbeat count | `176` |
| Master heartbeat latest | `2026-06-05T04:33:39Z` |
| Camera heartbeat latest | `2026-06-05T04:33:25Z` |
| Master uptime | `87029s` |
| Camera uptime | `135816s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-55 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `608 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `40` |
| Latest image proxy check | image `1692` HTTP `200`, `image/jpeg`, `63439` bytes, `1600x1200` |
| Commands since soak start | `39 completed`, `0 timed_out` |
| Command checkpoint | commands `377`, `378`, and `379` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 24-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1692`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed within budget, and no Cloud Run ERROR logs, command timeouts, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T05:02:55Z - 24.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `24h33m35s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-05T05:02:52Z` |
| Camera heartbeat latest | `2026-06-05T05:02:40Z` |
| Master uptime | `88781s` |
| Camera uptime | `137571s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-52 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `605 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `40` |
| Latest image proxy check | image `1692` HTTP `200`, `image/jpeg`, `63439` bytes, `1600x1200` |
| Commands since soak start | `39 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 26-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, latest authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T05:32:54Z - 25-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `25h03m34s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-05T05:32:50Z` |
| Camera heartbeat latest | `2026-06-05T05:32:40Z` |
| Master uptime | `90580s` |
| Camera uptime | `139371s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-63 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `600 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `41` |
| Latest image proxy check | image `1693` HTTP `200`, `image/jpeg`, `66885` bytes, `1600x1200` |
| Commands since soak start | `39 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 26-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, image uploads advanced to image `1693`, authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T06:03:25Z - 25.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `25h34m05s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T06:03:25Z` |
| Camera heartbeat latest | `2026-06-05T06:02:40Z` |
| Master uptime | `92414s` |
| Camera uptime | `141171s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `600 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `41` |
| Latest image proxy check | image `1693` HTTP `200`, `image/jpeg`, `66885` bytes, `1600x1200` |
| Commands since soak start | `39 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 26-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, latest authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections remained stable, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T06:34:38Z - 26-Hour Command Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `26h05m18s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `770` |
| Camera heartbeat count | `174` |
| Master heartbeat latest | `2026-06-05T06:34:28Z` |
| Camera heartbeat latest | `2026-06-05T06:34:11Z` |
| Master uptime | `94278s` |
| Camera uptime | `143062s` |
| Master RSSI | `-54 dBm` |
| Camera RSSI | `-62 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `704 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `43` |
| Latest image proxy check | image `1695` HTTP `200`, `image/jpeg`, `253224` bytes, `1600x1200` |
| Commands since soak start | `43 completed`, `0 timed_out` |
| Command checkpoint | commands `381`, `382`, and `383` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Additional command activity | command `380` light-off completed before this checkpoint; no timeout or duplicate execution evidence observed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | settled at `9` total, `1 active`, `8 idle`; `21/25` DB connections total after validation traffic |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean with DB connection count watch item. The 26-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1695`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, non-info diagnostics, OperationalError, QueuePool timeout, or connection exhaustion were observed. DB connections were elevated after validation traffic (`21/25` total after a short settle window), below the failure threshold but worth watching at the next checkpoint.

### 2026-06-05T07:03:24Z - 26.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `26h34m04s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `789` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-05T07:03:16Z` |
| Camera heartbeat latest | `2026-06-05T07:02:41Z` |
| Master uptime | `96005s` |
| Camera uptime | `144772s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `808 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `43` |
| Latest image proxy check | image `1695` HTTP `200`, `image/jpeg`, `253224` bytes, `1600x1200` |
| Commands since soak start | `43 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 28-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| DB connection watch item | returned to normal range after previous checkpoint elevation |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The prior DB connection watch item cleared: total connections returned to `17/25` with no `OperationalError`, QueuePool timeout, connection exhaustion, or Cloud Run ERROR logs. Both devices remained online with current heartbeats and progressing uptime, latest authenticated image proxy returned HTTP `200`, command polling stayed current, and no command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T07:33:24Z - 27-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `27h04m04s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `786` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-05T07:33:16Z` |
| Camera heartbeat latest | `2026-06-05T07:32:41Z` |
| Master uptime | `97805s` |
| Camera uptime | `146572s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `596 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `44` |
| Latest image proxy check | image `1696` HTTP `200`, `image/jpeg`, `65047` bytes, `1600x1200` |
| Commands since soak start | `43 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 28-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, image uploads advanced to image `1696`, authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, non-info diagnostics, OperationalError, QueuePool timeout, or connection exhaustion were observed.

### 2026-06-05T08:03:25Z - 27.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `27h34m05s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `788` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-05T08:03:17Z` |
| Camera heartbeat latest | `2026-06-05T08:02:41Z` |
| Master uptime | `99606s` |
| Camera uptime | `148372s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `596 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `44` |
| Latest image proxy check | image `1696` HTTP `200`, `image/jpeg`, `65047` bytes, `1600x1200` |
| Commands since soak start | `43 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 28-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, latest authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, non-info diagnostics, OperationalError, QueuePool timeout, or connection exhaustion were observed.

### 2026-06-05T08:34:41Z - 28-Hour Command Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `28h05m21s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `769` |
| Camera heartbeat count | `176` |
| Master heartbeat latest | `2026-06-05T08:34:36Z` |
| Camera heartbeat latest | `2026-06-05T08:34:11Z` |
| Master uptime | `101485s` |
| Camera uptime | `150262s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `604 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `46` |
| Latest image proxy check | image `1698` HTTP `200`, `image/jpeg`, `64895` bytes, `1600x1200` |
| Commands since soak start | `46 completed`, `0 timed_out` |
| Command checkpoint | commands `384`, `385`, and `386` completed; lifecycle evidence included queued, polled, sent, acked, completed command rows, and capture image upload |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 28-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1698`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, non-info diagnostics, OperationalError, QueuePool timeout, or connection exhaustion were observed.

### 2026-06-05T09:03:23Z - 28.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `28h34m03s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T09:03:15Z` |
| Camera heartbeat latest | `2026-06-05T09:02:41Z` |
| Master uptime | `103205s` |
| Camera uptime | `151972s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `709 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `46` |
| Latest image proxy check | image `1698` HTTP `200`, `image/jpeg`, `64895` bytes, `1600x1200` |
| Commands since soak start | `46 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 30-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, latest authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, non-info diagnostics, OperationalError, QueuePool timeout, or connection exhaustion were observed.

### 2026-06-05T09:33:24Z - 29-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `29h04m04s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T09:33:21Z` |
| Camera heartbeat latest | `2026-06-05T09:32:41Z` |
| Master uptime | `105010s` |
| Camera uptime | `153772s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `599 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `47` |
| Latest image proxy check | image `1699` HTTP `200`, `image/jpeg`, `63447` bytes, `1600x1200` |
| Commands since soak start | `46 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 30-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, image uploads advanced to image `1699`, authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, non-info diagnostics, OperationalError, QueuePool timeout, or connection exhaustion were observed.

### 2026-06-05T10:03:53Z - 29.5-Hour Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `29h34m33s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-05T10:03:48Z` |
| Camera heartbeat latest | `2026-06-05T10:03:26Z` |
| Master uptime | `106837s` |
| Camera uptime | `155617s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `803 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `47` |
| Latest image proxy check | image `1699` HTTP `200`, `image/jpeg`, `63447` bytes, `1600x1200` |
| Commands since soak start | `46 completed`, `0 timed_out` |
| Command checkpoint | not due; next command checkpoint expected around the 30-hour checkpoint |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both devices remained online with current heartbeats and progressing uptime, latest authenticated image proxy returned HTTP `200`, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, non-info diagnostics, OperationalError, QueuePool timeout, or connection exhaustion were observed.

### 2026-06-05T10:34:53Z - 30-Hour Command Checkpoint

| Check | Result |
| --- | --- |
| Elapsed soak time | `30h05m33s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `775` |
| Camera heartbeat count | `176` |
| Master heartbeat latest | `2026-06-05T10:34:47Z` |
| Camera heartbeat latest | `2026-06-05T10:34:11Z` |
| Master uptime | `108696s` |
| Camera uptime | `157462s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `806 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `49` |
| Latest image proxy check | image `1701` HTTP `200`, `image/jpeg`, `64248` bytes, `1600x1200` |
| Commands since soak start | `49 completed`, `0 timed_out` |
| Command checkpoint | commands `387`, `388`, and `389` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 30-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1701`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, non-info diagnostics, OperationalError, QueuePool timeout, or connection exhaustion were observed.

### 2026-06-05T11:03:54Z - 30.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `30h34m34s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T11:03:49Z` |
| Camera heartbeat latest | `2026-06-05T11:03:29Z` |
| Master uptime | `110438s` |
| Camera uptime | `159217s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-56 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `598 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `49` |
| Latest image proxy check | image `1701` HTTP `200`, `image/jpeg`, `64248` bytes, `1600x1200` |
| Commands since soak start | `49 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 30-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `2 active`, `3 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Both health endpoints and provisioning health returned OK; authenticated proxy loading for image `1701` returned HTTP `200`; devices remained online with current heartbeats and progressing uptime; command polling stayed current; Cloud SQL connections remained stable; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T11:33:53Z - 31-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `31h04m33s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-05T11:33:46Z` |
| Camera heartbeat latest | `2026-06-05T11:33:26Z` |
| Master uptime | `112236s` |
| Camera uptime | `161017s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `597 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `50` |
| Latest image proxy check | image `1702` HTTP `200`, `image/jpeg`, `64798` bytes, `1600x1200` |
| Commands since soak start | `49 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 30-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1702`, and the authenticated proxy returned HTTP `200`. Backend, provisioning, master, and camera remained healthy; command polling stayed current; DB connections remained stable; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T12:03:53Z - 31.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `31h34m33s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T12:03:52Z` |
| Camera heartbeat latest | `2026-06-05T12:03:26Z` |
| Master uptime | `114041s` |
| Camera uptime | `162817s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `597 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `50` |
| Latest image proxy check | image `1702` HTTP `200`, `image/jpeg`, `64798` bytes, `1600x1200` |
| Commands since soak start | `49 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 30-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `2 active`, `3 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Devices remained online with current heartbeats and progressing uptime; backend and provisioning revisions stayed on the expected production revisions; command polling remained current; image proxy access for image `1702` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T12:33:56Z - 32-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `32h04m36s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T12:33:54Z` |
| Camera heartbeat latest | `2026-06-05T12:33:26Z` |
| Master uptime | `115843s` |
| Camera uptime | `164617s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `606 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `52` |
| Latest image proxy check | image `1704` HTTP `200`, `image/jpeg`, `64981` bytes, `1600x1200` |
| Commands since soak start | `52 completed`, `0 timed_out` |
| Command checkpoint | commands `390`, `391`, and `392` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle`; `15/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 32-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1704`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T13:03:54Z - 32.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `32h34m34s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T13:03:49Z` |
| Camera heartbeat latest | `2026-06-05T13:03:26Z` |
| Master uptime | `117638s` |
| Camera uptime | `166417s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `1010 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `52` |
| Latest image proxy check | image `1704` HTTP `200`, `image/jpeg`, `64981` bytes, `1600x1200` |
| Commands since soak start | `52 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 32-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning stayed on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling stayed current with `command_poll_stale_seconds=0`; authenticated proxy access for image `1704` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T13:33:53Z - 33-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `33h04m33s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `789` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T13:33:42Z` |
| Camera heartbeat latest | `2026-06-05T13:33:26Z` |
| Master uptime | `119432s` |
| Camera uptime | `168217s` |
| Master RSSI | `-46 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `710 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `53` |
| Latest image proxy check | image `1705` HTTP `200`, `image/jpeg`, `65173` bytes, `1600x1200` |
| Commands since soak start | `52 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 32-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `3 active`, `1 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1705`, and authenticated proxy access returned HTTP `200`. Backend and provisioning stayed on the expected revisions; devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T14:03:55Z - 33.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `33h34m35s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T14:03:51Z` |
| Camera heartbeat latest | `2026-06-05T14:03:26Z` |
| Master uptime | `121240s` |
| Camera uptime | `170017s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `603 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `53` |
| Latest image proxy check | image `1705` HTTP `200`, `image/jpeg`, `65173` bytes, `1600x1200` |
| Commands since soak start | `52 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 32-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle`; `15/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1705` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T14:34:01Z - 34-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `34h04m41s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T14:34:00Z` |
| Camera heartbeat latest | `2026-06-05T14:33:26Z` |
| Master uptime | `123049s` |
| Camera uptime | `171817s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `664 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `55` |
| Latest image proxy check | image `1707` HTTP `200`, `image/jpeg`, `70894` bytes, `1600x1200` |
| Commands since soak start | `55 completed`, `0 timed_out` |
| Command checkpoint | commands `393`, `394`, and `395` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle`; `15/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 34-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1707`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T15:03:55Z - 34.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `34h34m35s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T15:03:54Z` |
| Camera heartbeat latest | `2026-06-05T15:03:26Z` |
| Master uptime | `124843s` |
| Camera uptime | `173617s` |
| Master RSSI | `-47 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `692 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `55` |
| Latest image proxy check | image `1707` HTTP `200`, `image/jpeg`, `70894` bytes, `1600x1200` |
| Commands since soak start | `55 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 34-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1707` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T15:33:59Z - 35-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `35h04m39s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `790` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T15:33:58Z` |
| Camera heartbeat latest | `2026-06-05T15:33:26Z` |
| Master uptime | `126648s` |
| Camera uptime | `175417s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-67 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `707 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `56` |
| Latest image proxy check | image `1708` HTTP `200`, `image/jpeg`, `71784` bytes, `1600x1200` |
| Commands since soak start | `55 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 34-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1708`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T16:03:56Z - 35.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `35h34m36s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-05T16:03:47Z` |
| Camera heartbeat latest | `2026-06-05T16:03:26Z` |
| Master uptime | `128436s` |
| Camera uptime | `177217s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-54 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `594 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `56` |
| Latest image proxy check | image `1708` HTTP `200`, `image/jpeg`, `71784` bytes, `1600x1200` |
| Commands since soak start | `55 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 34-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1708` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T16:33:57Z - 36-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `36h04m37s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `789` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-05T16:33:52Z` |
| Camera heartbeat latest | `2026-06-05T16:33:26Z` |
| Master uptime | `130241s` |
| Camera uptime | `179017s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-54 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `612 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `58` |
| Latest image proxy check | image `1710` HTTP `200`, `image/jpeg`, `71714` bytes, `1600x1200` |
| Commands since soak start | `58 completed`, `0 timed_out` |
| Command checkpoint | commands `396`, `397`, and `398` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 36-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1710`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T17:03:56Z - 36.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `36h34m36s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `182` |
| Master heartbeat latest | `2026-06-05T17:03:47Z` |
| Camera heartbeat latest | `2026-06-05T17:03:26Z` |
| Master uptime | `132036s` |
| Camera uptime | `180817s` |
| Master RSSI | `-56 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `801 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `58` |
| Latest image proxy check | image `1710` HTTP `200`, `image/jpeg`, `71714` bytes, `1600x1200` |
| Commands since soak start | `58 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 36-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1710` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T17:34:25Z - 37-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `37h05m05s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T17:34:20Z` |
| Camera heartbeat latest | `2026-06-05T17:34:11Z` |
| Master uptime | `133869s` |
| Camera uptime | `182662s` |
| Master RSSI | `-59 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `806 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `59` |
| Latest image proxy check | image `1711` HTTP `200`, `image/jpeg`, `70698` bytes, `1600x1200` |
| Commands since soak start | `58 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 36-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1711`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T18:04:30Z - 37.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `37h35m10s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T18:04:20Z` |
| Camera heartbeat latest | `2026-06-05T18:04:11Z` |
| Master uptime | `135669s` |
| Camera uptime | `184462s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-54 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `715 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `59` |
| Latest image proxy check | image `1711` HTTP `200`, `image/jpeg`, `70698` bytes, `1600x1200` |
| Commands since soak start | `58 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 36-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1711` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T18:34:29Z - 38-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `38h05m09s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-05T18:34:25Z` |
| Camera heartbeat latest | `2026-06-05T18:34:11Z` |
| Master uptime | `137474s` |
| Camera uptime | `186262s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-65 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `589 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `61` |
| Latest image proxy check | image `1713` HTTP `200`, `image/jpeg`, `66473` bytes, `1600x1200` |
| Commands since soak start | `61 completed`, `0 timed_out` |
| Command checkpoint | commands `399`, `400`, and `401` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 38-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1713`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T19:04:27Z - 38.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `38h35m07s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T19:04:19Z` |
| Camera heartbeat latest | `2026-06-05T19:04:11Z` |
| Master uptime | `139269s` |
| Camera uptime | `188062s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `596 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `61` |
| Latest image proxy check | image `1713` HTTP `200`, `image/jpeg`, `66473` bytes, `1600x1200` |
| Commands since soak start | `61 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 38-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1713` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T19:34:34Z - 39-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `39h05m14s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-05T19:34:28Z` |
| Camera heartbeat latest | `2026-06-05T19:34:11Z` |
| Master uptime | `141077s` |
| Camera uptime | `189862s` |
| Master RSSI | `-53 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `806 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `62` |
| Latest image proxy check | image `1714` HTTP `200`, `image/jpeg`, `71704` bytes, `1600x1200` |
| Commands since soak start | `61 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 38-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1714`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T20:04:28Z - 39.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `39h35m08s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `796` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-05T20:04:22Z` |
| Camera heartbeat latest | `2026-06-05T20:04:11Z` |
| Master uptime | `142871s` |
| Camera uptime | `191662s` |
| Master RSSI | `-56 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `606 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `62` |
| Latest image proxy check | image `1714` HTTP `200`, `image/jpeg`, `71704` bytes, `1600x1200` |
| Commands since soak start | `61 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 38-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1714` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T20:34:28Z - 40-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `40h05m08s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-05T20:34:24Z` |
| Camera heartbeat latest | `2026-06-05T20:34:11Z` |
| Master uptime | `144673s` |
| Camera uptime | `193462s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-63 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `644 ms` |
| `command_poll_stale_seconds` | `1` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `64` |
| Latest image proxy check | image `1716` HTTP `200`, `image/jpeg`, `67221` bytes, `1600x1200` |
| Commands since soak start | `64 completed`, `0 timed_out` |
| Command checkpoint | commands `402`, `403`, and `404` completed; lifecycle events included queued, polled, sent, acked, and completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. The 40-hour command checkpoint passed: diagnostics, capture, and light intensity commands completed; capture produced image `1716`, and authenticated image proxy returned HTTP `200`. Both devices remained online with current heartbeats and progressing uptime, command polling stayed current, DB connections stayed in normal range, and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T21:04:28Z - 40.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `40h35m08s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `796` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-05T21:04:27Z` |
| Camera heartbeat latest | `2026-06-05T21:04:11Z` |
| Master uptime | `146476s` |
| Camera uptime | `195262s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-64 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `703 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `64` |
| Latest image proxy check | image `1716` HTTP `200`, `image/jpeg`, `67221` bytes, `1600x1200` |
| Commands since soak start | `64 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 40-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1716` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T21:34:29Z - 41-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `41h05m09s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-05T21:34:26Z` |
| Camera heartbeat latest | `2026-06-05T21:34:11Z` |
| Master uptime | `148276s` |
| Camera uptime | `197062s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-62 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `600 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `65` |
| Latest image proxy check | image `1717` HTTP `200`, `image/jpeg`, `66384` bytes, `1600x1200` |
| Commands since soak start | `64 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 40-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1717`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T22:04:28Z - 41.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `41h35m08s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `796` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-05T22:04:20Z` |
| Camera heartbeat latest | `2026-06-05T22:04:11Z` |
| Master uptime | `150069s` |
| Camera uptime | `198862s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-61 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `900 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `65` |
| Latest image proxy check | image `1717` HTTP `200`, `image/jpeg`, `66384` bytes, `1600x1200` |
| Commands since soak start | `64 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 40-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1717` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T22:36:48Z - 42-Hour Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `42h07m28s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `775` |
| Camera heartbeat count | `177` |
| Master heartbeat latest | `2026-06-05T22:36:42Z` |
| Camera heartbeat latest | `2026-06-05T22:36:26Z` |
| Master uptime | `152011s` |
| Camera uptime | `200798s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-62 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `906 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `67` |
| Latest image proxy check | image `1719` HTTP `200`, `image/jpeg`, `67689` bytes, `1600x1200` |
| Commands since soak start | `67 completed`, `0 timed_out` |
| Command checkpoint | commands `405` diagnostics, `406` capture, and `407` light completed with queued, polled, sent, acked, and completed telemetry |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle`; `15/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Commands `405`, `406`, and `407` completed without timeout, and command telemetry recorded queued, polled, sent, acked, and completed states. Image `1719` uploaded from the camera and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T23:04:22Z - 42.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `42h35m02s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-05T23:04:16Z` |
| Camera heartbeat latest | `2026-06-05T23:04:11Z` |
| Master uptime | `153665s` |
| Camera uptime | `202463s` |
| Master RSSI | `-48 dBm` |
| Camera RSSI | `-61 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `1005 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `67` |
| Latest image proxy check | image `1719` HTTP `200`, `image/jpeg`, `67689` bytes, `1600x1200` |
| Commands since soak start | `67 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 42-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1719` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-05T23:34:31Z - 43-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `43h05m11s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `792` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-05T23:34:24Z` |
| Camera heartbeat latest | `2026-06-05T23:34:11Z` |
| Master uptime | `155474s` |
| Camera uptime | `204263s` |
| Master RSSI | `-49 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `594 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `68` |
| Latest image proxy check | image `1720` HTTP `200`, `image/jpeg`, `67241` bytes, `1600x1200` |
| Commands since soak start | `67 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 42-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1720`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T00:04:33Z - 43.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `43h35m13s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `795` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-06T00:04:22Z` |
| Camera heartbeat latest | `2026-06-06T00:04:11Z` |
| Master uptime | `157271s` |
| Camera uptime | `206063s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `596 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `68` |
| Latest image proxy check | image `1720` HTTP `200`, `image/jpeg`, `67241` bytes, `1600x1200` |
| Commands since soak start | `67 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 42-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1720` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T00:34:31Z - 44-Hour Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `44h05m11s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `794` |
| Camera heartbeat count | `178` |
| Master heartbeat latest | `2026-06-06T00:34:22Z` |
| Camera heartbeat latest | `2026-06-06T00:34:13Z` |
| Master uptime | `159071s` |
| Camera uptime | `207864s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `656 ms` |
| `command_poll_stale_seconds` | `1` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `70` |
| Latest image proxy check | image `1722` HTTP `200`, `image/jpeg`, `66592` bytes, `1600x1200` |
| Commands since soak start | `70 completed`, `0 timed_out` |
| Command checkpoint | commands `408` diagnostics, `409` capture, and `410` light completed with queued, polled, sent, acked, and completed telemetry |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle`; `15/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Commands `408`, `409`, and `410` completed without timeout, and command telemetry recorded queued, polled, sent, acked, and completed states. Capture command `409` produced image `1722`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling remained healthy with no `COMMAND_POLL_STALE` event; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T01:04:31Z - 44.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `44h35m11s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `797` |
| Camera heartbeat count | `178` |
| Master heartbeat latest | `2026-06-06T01:04:22Z` |
| Camera heartbeat latest | `2026-06-06T01:04:13Z` |
| Master uptime | `160871s` |
| Camera uptime | `209664s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-57 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `696 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `70` |
| Latest image proxy check | image `1722` HTTP `200`, `image/jpeg`, `66592` bytes, `1600x1200` |
| Commands since soak start | `70 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 44-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `2 active`, `3 idle`; `17/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1722` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T01:34:31Z - 45-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `45h05m11s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `795` |
| Camera heartbeat count | `177` |
| Master heartbeat latest | `2026-06-06T01:34:25Z` |
| Camera heartbeat latest | `2026-06-06T01:34:13Z` |
| Master uptime | `162674s` |
| Camera uptime | `211464s` |
| Master RSSI | `-50 dBm` |
| Camera RSSI | `-59 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `911 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `71` |
| Latest image proxy check | image `1723` HTTP `200`, `image/jpeg`, `66476` bytes, `1600x1200` |
| Commands since soak start | `70 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 44-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1723`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T02:04:37Z - 45.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `45h35m17s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `797` |
| Camera heartbeat count | `178` |
| Master heartbeat latest | `2026-06-06T02:04:31Z` |
| Camera heartbeat latest | `2026-06-06T02:04:13Z` |
| Master uptime | `164480s` |
| Camera uptime | `213264s` |
| Master RSSI | `-63 dBm` |
| Camera RSSI | `-68 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `607 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `71` |
| Latest image proxy check | image `1723` HTTP `200`, `image/jpeg`, `66476` bytes, `1600x1200` |
| Commands since soak start | `70 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 44-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1723` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T02:34:25Z - 46-Hour Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `46h05m05s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `793` |
| Camera heartbeat count | `179` |
| Master heartbeat latest | `2026-06-06T02:34:16Z` |
| Camera heartbeat latest | `2026-06-06T02:34:13Z` |
| Master uptime | `166265s` |
| Camera uptime | `215064s` |
| Master RSSI | `-51 dBm` |
| Camera RSSI | `-53 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `609 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `73` |
| Latest image proxy check | image `1725` HTTP `200`, `image/jpeg`, `67152` bytes, `1600x1200` |
| Commands since soak start | `73 completed`, `0 timed_out` |
| Command checkpoint | commands `411` diagnostics, `412` capture, and `413` light completed with queued, polled, sent, acked, and completed telemetry |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle`; `15/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Commands `411`, `412`, and `413` completed without timeout, and command telemetry recorded queued, polled, sent, acked, and completed states. Capture command `412` produced image `1725`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T03:04:33Z - 46.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `46h35m13s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `795` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-06T03:04:33Z` |
| Camera heartbeat latest | `2026-06-06T03:04:13Z` |
| Master uptime | `168082s` |
| Camera uptime | `216864s` |
| Master RSSI | `-52 dBm` |
| Camera RSSI | `-55 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `622 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `73` |
| Latest image proxy check | image `1725` HTTP `200`, `image/jpeg`, `67152` bytes, `1600x1200` |
| Commands since soak start | `73 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 46-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `4` total, `1 active`, `3 idle`; `16/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1725` passed; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T03:34:42Z - 47-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `47h05m22s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `789` |
| Camera heartbeat count | `180` |
| Master heartbeat latest | `2026-06-06T03:34:36Z` |
| Camera heartbeat latest | `2026-06-06T03:34:14Z` |
| Master uptime | `169885s` |
| Camera uptime | `218666s` |
| Master RSSI | `-58 dBm` |
| Camera RSSI | `-58 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `613 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `75` |
| Latest image proxy check | image `1727` HTTP `200`, `image/jpeg`, `66374` bytes, `1600x1200` |
| Commands since soak start | `73 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 46-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | initial sample `11` total, `2 active`, `9 idle`; `23/25` DB connections total; follow-up samples stabilized at `9` total, `1 active`, `8 idle`; `21/25` total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Latest scheduled image upload advanced to image `1727`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections were elevated but remained below the configured maximum with no DB error logs; and no Cloud Run ERROR logs, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T04:04:42Z - 47.5-Hour Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `47h35m22s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `791` |
| Camera heartbeat count | `181` |
| Master heartbeat latest | `2026-06-06T04:04:32Z` |
| Camera heartbeat latest | `2026-06-06T04:04:14Z` |
| Master uptime | `171681s` |
| Camera uptime | `220466s` |
| Master RSSI | `-56 dBm` |
| Camera RSSI | `-51 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `1023 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `75` |
| Latest image proxy check | image `1727` HTTP `200`, `image/jpeg`, `66374` bytes, `1600x1200` |
| Commands since soak start | `73 completed`, `0 timed_out` |
| Command checkpoint | not due; previous 46-hour command set completed |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `5` total, `1 active`, `4 idle`; `17/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Checkpoint result: clean. Backend and provisioning remained on the expected revisions; health endpoints returned OK; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; authenticated proxy access for image `1727` passed; DB connections returned below the prior elevated sample and stayed within budget; and no Cloud Run ERROR logs, DB connection errors, command timeouts, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

### 2026-06-06T04:34:55Z - 48-Hour Final Command Checkpoint

| Metric | Value |
| --- | ---: |
| Elapsed soak time | `48h05m35s` |
| Backend revision | `plantlab-api-00080-hej` at `100%` traffic |
| Provisioning revision | `plantlab-provision-api-00021-bis` at `100%` traffic |
| Master firmware | `0.1.6` |
| Camera firmware | `0.1.8` |
| Master status | `online` |
| Camera status | `online` |
| Master heartbeat count | `786` |
| Camera heartbeat count | `183` |
| Master heartbeat latest | `2026-06-06T04:34:27Z` |
| Camera heartbeat latest | `2026-06-06T04:34:14Z` |
| Master uptime | `173476s` |
| Camera uptime | `222266s` |
| Master RSSI | `-57 dBm` |
| Camera RSSI | `-54 dBm` |
| Master command poll status | `ok` |
| Master command poll latency | `600 ms` |
| `command_poll_stale_seconds` | `0` |
| Master NTP | `synchronized`, `last_ntp_sync_at=2026-06-04T04:23:22Z` |
| Camera NTP | `synchronized`, `last_ntp_sync_at=2026-06-03T14:49:57Z` |
| Images uploaded since soak start | `77` |
| Latest image proxy check | image `1729` HTTP `200`, `image/jpeg`, `64981` bytes, `1600x1200` |
| Commands since soak start | `76 completed`, `0 timed_out` |
| Command checkpoint | commands `414` diagnostics, `415` capture, and `416` light completed with queued, polled, sent, acked, and completed telemetry |
| Cloud Run ERROR logs since start | `0` |
| DB PlantLab connections | `3` total, `1 active`, `2 idle`; `15/25` DB connections total |
| DB connection error logs since start | `0` `OperationalError`, `QueuePool`, connection exhaustion, or too-many-connections matches |
| `COMMAND_POLL_STALE` | `0` |
| Non-info diagnostics | `0` |
| OTA events | `0` |
| Health endpoints | PASS |
| `git diff --check` | PASS |

Final result: PASSED. The full 48-hour release-candidate soak completed cleanly after the final command checkpoint. Commands `414`, `415`, and `416` completed without timeout, and command telemetry recorded queued, polled, sent, acked, and completed states. Capture command `415` produced image `1729`, and authenticated proxy access returned HTTP `200`. Backend and provisioning remained on the expected revisions; both devices remained online with current heartbeats and progressing uptime; command polling stayed current; DB connections stayed within budget; and no Cloud Run ERROR logs, DB connection errors, `COMMAND_POLL_STALE`, OTA activity, or non-info diagnostics were observed.

## Monitoring Instructions

Every 30 minutes:

```bash
SOAK_STARTED_AT=2026-06-04T04:29:20Z scripts/testing/gcp_48h_soak_snapshot.sh
git diff --check
```

Verify:

- backend revision `plantlab-api-00080-hej` remains healthy
- provisioning revision `plantlab-provision-api-00021-bis` remains healthy
- master `pl-esp32-64e0a80af6e8` firmware `0.1.6` remains online and healthy
- camera `pl-cam-1c1df816a398` firmware `0.1.8` remains online and healthy
- camera NTP remains synchronized with `last_ntp_sync_at` present
- heartbeats are current and uptime progresses
- image uploads continue and authenticated proxy image URLs load
- command polling telemetry remains healthy
- no command timeouts occur
- no `COMMAND_POLL_STALE` appears
- no OTA retry, OTA failure, or unexpected OTA events appear
- no non-info diagnostics persist
- Cloud Run ERROR logs remain `0`
- Cloud SQL connection count stays stable with no `OperationalError`, QueuePool timeout, or connection exhaustion

At command checkpoints, issue:

- `REQUEST_DIAGNOSTICS`
- `CAPTURE_IMAGE`
- `SET_LIGHT_BRIGHTNESS`

Failure conditions:

- Cloud Run ERROR log
- DB connection error
- command timeout
- `COMMAND_POLL_STALE`
- image upload failure
- reboot loop
- repeated disconnects
- persistent non-info diagnostics
- unexpected OTA activity
- storage corruption

If a failure condition appears, stop the soak, update `docs/testing/reliability_issues.md`, classify severity, and do not apply speculative fixes.
