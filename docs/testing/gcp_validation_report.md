# PlantLab GCP Validation Report

Validation phase: Reliability Validation Phase 3 - GCP Deployment + Simulator Stress Validation

Started: 2026-05-30T06:59:53Z

Release commit under validation: `1871ea1`

## Gate Summary

| Gate | Status | Result |
| --- | --- | --- |
| Gate 1 - Deployment readiness audit | PASS | GCP resources, secrets, deployment scripts, and baseline service state verified. |
| Gate 2 - Database migration validation | PASS | Backup, migration job, and read-only schema verification succeeded. |
| Gate 3 - Deploy backend | PASS | Platform and provisioning backend candidates deployed, health-checked, and shifted to 100% traffic. |
| Gate 4 - Deploy web | PASS | Web image built, deployed, route-checked, asset-checked, and shifted to 100% traffic. |
| Gate 5 - Cloud smoke validation | PASS | Core APIs, signed image download, image upload, timeline, OTA manifest, and command lifecycle passed after hotfix. |
| Gate 6 - Simulator validation, 1 device | PASS | 15-minute one-master/one-camera simulator run completed with healthy nodes, images, timeline events, and no backend ERROR logs. |
| Gate 7 - Simulator validation, 5 devices | PASS | 30-minute 5-master/5-camera simulator run completed with healthy nodes, 50 recent images checked, filtered image timeline available, and no backend ERROR logs. |
| Gate 8 - Simulator validation, 20 devices | PASS | 30-minute 20-master/20-camera scenario stress completed without simulator warnings or backend ERROR logs; image uploads and timeline filters remained functional. |
| Gate 9 - Simulator OTA validation | PASS | START_OTA initially exposed a cloud migration gap; after migration fix, simulator OTA command and OTA_STATUS lifecycle completed successfully. |
| Gate 10 - Image upload validation | PASS | Image-focused cloud simulator run completed; signed image URLs, downloads, metadata, image timeline, and backend logs passed. |

## Gate 1 - Deployment Readiness Audit

Status: PASS

Executed checks:

- `git status --short --branch`
- `platform/infra/cloud-run/deploy_backend.sh print-config`
- `platform/infra/cloud-run/deploy_backend.sh preflight`
- `platform/infra/cloud-run/deploy_provisioning_backend.sh print-config`
- `platform/infra/cloud-run/deploy_provisioning_backend.sh preflight`
- `gcloud run services list --region us-central1`
- `gcloud run jobs list --region us-central1`
- `gcloud run services describe plantlab-api --region us-central1`
- `gcloud run services describe plantlab-provision-api --region us-central1`
- `gcloud run services describe plantlab-web --region us-central1`
- `cd platform/backend && ../../.venv/bin/alembic heads`

Baseline:

- Active GCP project: `plantlab-493805`
- Active GCP account: `lvganglvgang@gmail.com`
- Region: `us-central1`
- Artifact Registry repo: `plantlab-repo`
- Cloud SQL instance: `plantlab`
- Cloud SQL database: `plantlab`
- Cloud SQL connection name: `plantlab-493805:us-central1:plantlab`
- Cloud SQL state: `RUNNABLE`
- Cloud SQL backups: enabled with point-in-time recovery
- GCS image and firmware bucket: `gs://plantlab-images-garylu/`
- Runtime service account: `plantlab-run-sa@plantlab-493805.iam.gserviceaccount.com`
- Provisioning API: `https://plantlab-provision-api-418533861080.us-central1.run.app`
- Device platform URL configured for production: `https://api.marspotatolab.com`
- Standalone web origin regex: `^https://(marspotatolab\.com|app\.marspotatolab\.com)$`
- Alembic head in current repo: `20260527_0012`

Verified GCP services:

- Cloud Run Admin API
- Artifact Registry API
- Cloud SQL Admin API
- Secret Manager API
- Cloud Build API
- Cloud Storage API

Verified Secret Manager secret presence:

- `db-password`
- `app-secret-key`
- `google-oauth-client-id`
- `google-oauth-client-secret`
- `provisioning-shared-secret`

Current deployed services:

- `plantlab-api`: ready, 100% traffic to `plantlab-api-00053-bib`, image `plantlab-api:e11abe3-20260525003133`
- `plantlab-provision-api`: ready, 100% traffic to `plantlab-provision-api-00017-bej`, image `plantlab-provision-api:fe65be5-provision-20260522002341`
- `plantlab-web`: ready, 100% traffic to `plantlab-web-00010-ciy`, image `plantlab-web:8951455-web-20260525164638`

Readiness notes:

- Backend deployment helper supports build, backup, migration job, no-traffic candidate deployment, health verification, traffic shift, and rollback.
- Provisioning deployment helper supports the provisioning service lifecycle and passed preflight.
- Production OTA publishing support is present in `platform/infra/scripts/ota_release.py`.
- Staged OTA migration is present as `20260527_0012_staged_ota_rollout.py`.
- The command value column exists in the initial migration and is already part of the base schema.
- No dedicated web deployment helper exists in the repo. The live `plantlab-web` Cloud Run service exists and can be deployed with the existing `platform/infra/docker/Dockerfile.web` via Cloud Build in Gate 4.

Gate 1 result:

No deployment blockers found. Safe to proceed to Gate 2.

## Gate 2 - Database Migration Validation

Status: PASS

Executed checks:

- `platform/infra/cloud-run/deploy_backend.sh test-local`
- `platform/infra/cloud-run/deploy_backend.sh build`
- `platform/infra/cloud-run/deploy_backend.sh backup`
- `platform/infra/cloud-run/deploy_backend.sh migrate`
- `gcloud run jobs execute plantlab-schema-check --region us-central1 --wait`
- `gcloud logging read ... plantlab-schema-check-n8xt6`

Results:

- Backend local tests: 270 passed.
- Backend image built and pushed: `us-central1-docker.pkg.dev/plantlab-493805/plantlab-repo/plantlab-api:1871ea1-20260530070034`
- Cloud Build ID: `12c08582-8e06-4800-98ea-dd3b0c412e20`
- Cloud SQL backup: completed before migration.
- Migration execution: `plantlab-api-migrate-dhz49`, completed successfully.
- Read-only schema check execution: `plantlab-schema-check-n8xt6`, completed successfully.
- Verified `alembic_version`: `20260527_0012`
- Verified tables:
  - `commands`
  - `firmware_releases`
  - `images`
  - `device_diagnostic_events`
  - `device_diagnostic_snapshots`
- Verified staged OTA rollout columns on `firmware_releases`.
- Verified `commands.value` column.

Notes:

- Initial schema-check job attempt `plantlab-schema-check-vlhqz` failed because the verifier job omitted the non-secret `GOOGLE_OAUTH_CLIENT_ID` while mounting `GOOGLE_OAUTH_CLIENT_SECRET`. This was a validation-command configuration error, not an application or migration failure. The job was corrected and rerun successfully.
- Backend Cloud Build submitted a large source archive because the current backend build submits the repo root. This is inefficient but did not block deployment.

Gate 2 result:

Database migration is healthy. Safe to proceed to Gate 3.

## Gate 3 - Deploy Backend

Status: PASS

Scope:

- Platform API: `plantlab-api`
- Provisioning API: `plantlab-provision-api`

Executed checks:

- `platform/infra/cloud-run/deploy_backend.sh deploy-candidate`
- `VERIFY_URL=https://candidate---plantlab-api-efvri7f4ma-uc.a.run.app platform/infra/cloud-run/deploy_backend.sh verify-health`
- `platform/infra/cloud-run/deploy_provisioning_backend.sh test-local`
- `platform/infra/cloud-run/deploy_provisioning_backend.sh build`
- `platform/infra/cloud-run/deploy_provisioning_backend.sh deploy-candidate`
- `VERIFY_URL=https://candidate---plantlab-provision-api-efvri7f4ma-uc.a.run.app platform/infra/cloud-run/deploy_provisioning_backend.sh verify-health`
- `CONFIRM_SHIFT_TRAFFIC=yes platform/infra/cloud-run/deploy_provisioning_backend.sh shift-traffic`
- `CONFIRM_SHIFT_TRAFFIC=yes platform/infra/cloud-run/deploy_backend.sh shift-traffic`
- `curl -fsS https://api.marspotatolab.com/health`
- `curl -fsS https://api.marspotatolab.com/api/health`
- `curl -fsS https://plantlab-provision-api-418533861080.us-central1.run.app/health`
- `gcloud logging read ... severity>=ERROR`

Results:

- Platform candidate revision: `plantlab-api-00055-guj`
- Platform candidate health: PASS
- Platform production traffic: 100% to `plantlab-api-00055-guj`
- Provisioning local tests: 9 passed.
- Provisioning image built and pushed: `us-central1-docker.pkg.dev/plantlab-493805/plantlab-repo/plantlab-provision-api:1871ea1-provision-20260530071840`
- Provisioning Cloud Build ID: `ecd7ee29-00dc-4b6a-95e6-90530f9aed5f`
- Provisioning candidate revision: `plantlab-provision-api-00019-nuv`
- Provisioning candidate health: PASS
- Provisioning production traffic: 100% to `plantlab-provision-api-00019-nuv`
- Production platform health endpoint: PASS
- Production provisioning health endpoint: PASS
- Recent Cloud Run ERROR logs after deploy: none returned.

Gate 3 result:

Backend services are healthy on current release images. Safe to proceed to Gate 4.

## Gate 4 - Deploy Web

Status: PASS

Executed checks:

- `npm --prefix platform/web run typecheck`
- `npm --prefix platform/web run build`
- Temporary reduced-context Cloud Build using `platform/infra/docker/Dockerfile.web`
- `gcloud run deploy plantlab-web ... --no-traffic --tag candidate --port 5173`
- Candidate route checks for `/`, `/demo`, and `/login`
- Candidate asset checks for primary JS/CSS
- `gcloud run services update-traffic plantlab-web --region us-central1 --to-tags candidate=100`
- Production route checks for:
  - `https://marspotatolab.com/`
  - `https://marspotatolab.com/demo`
  - `https://marspotatolab.com/login`
  - `https://plantlab-web-efvri7f4ma-uc.a.run.app/`
  - `https://plantlab-web-efvri7f4ma-uc.a.run.app/demo`
- Demo image asset spot checks.
- Recent Cloud Run ERROR log check for the new web revision.

Results:

- Web typecheck: PASS
- Web production build: PASS
- Web image built and pushed: `us-central1-docker.pkg.dev/plantlab-493805/plantlab-repo/plantlab-web:1871ea1-web-20260530072043`
- Web Cloud Build ID: `2094220f-5631-4c5e-ae97-f65a294e5c18`
- Web candidate revision: `plantlab-web-00012-hij`
- Candidate route checks: PASS, HTTP 200 for `/`, `/demo`, `/login`
- Candidate JS/CSS checks: PASS, HTTP 200
- Production traffic: 100% to `plantlab-web-00012-hij`
- Production custom domain route checks: PASS, HTTP 200
- Demo image asset spot checks: PASS, HTTP 200
- Recent Cloud Run ERROR logs for `plantlab-web-00012-hij`: none returned.

Notes:

- The repo does not currently include a dedicated web Cloud Run deployment helper. Gate 4 used a temporary Cloud Build config and reduced build context to avoid uploading local `node_modules` or unrelated repo data.
- A first candidate-check command failed locally because a zsh loop variable named `path` overwrote zsh's special path/PATH parameter. The check was rerun with a safe variable name and passed.

Gate 4 result:

Web is healthy on the current release image. Safe to proceed to Gate 5.

## Gate 5 - Cloud Smoke Validation

Status: PASS

Executed checks:

- Created a dedicated cloud simulator validation user/device through a one-off Cloud Run job.
- Issued a temporary access token for authenticated API smoke checks through a one-off Cloud Run job.
- Ran a 1-master/1-camera simulator smoke run against `https://api.marspotatolab.com`.
- Checked:
  - `GET /api/health`
  - `GET /api/devices`
  - `GET /api/devices/{id}/summary`
  - `GET /api/devices/{id}/timeline?limit=10`
  - `GET /api/devices/{id}/images?limit=5`
  - `GET /api/devices/{id}/commands?limit=5`
  - `GET /api/hardware/ota/manifest?...`
  - `POST /api/devices/{id}/commands/light`
- Reran simulator command polling to complete the queued command.
- Checked Cloud Run ERROR logs after API smoke.

Results so far:

- Cloud simulator device id: `35`
- Simulator registered one master and one camera node.
- Simulator posted sensor readings, diagnostics, heartbeats, and fake images.
- Image uploads observed: `1252`, `1253`, `1254`, `1255`
- Core API smoke checks returned HTTP 200 or 201.
- Light command completed:
  - command id: `234`
  - target/action: `light:set_intensity`
  - status: `completed`
- Timeline API returned recent events.

Issue found:

- `REL-GCP-001`: Cloud image APIs fell back to authenticated proxy URLs because Cloud Run metadata credentials needed explicit `cloud-platform` scoping and actual service account email resolution for IAM signed GCS URLs.

Fix applied:

- Backend image storage now scopes metadata credentials for IAM signing and resolves the actual Cloud Run service account email from the metadata server when credentials report `default`.
- Focused image tests passed with `23 passed`.
- Backend full test suite passed with `272 passed`.
- Backend hotfix revision `plantlab-api-00062-yoh` deployed to 100% production traffic.
- Image API now returns signed GCS URLs for images `1253`, `1254`, and `1255`.
- ERROR log check for `plantlab-api-00062-yoh` returned no errors after retest.

Final smoke rerun:

- Core API checks: PASS
- OTA manifest endpoint: PASS for registered simulator master node.
- Signed image URL download: PASS, downloaded non-empty image content through GCS signed URL.
- Command lifecycle: PASS, light command `235` was received, acked, and completed by the simulator.
- Additional image uploads after hotfix: `1256`, `1257`
- Timeline check: PASS, returned recent events after command/image activity.
- Cloud Run ERROR logs for `plantlab-api-00062-yoh`: none returned after retest.

Gate 5 result:

Cloud smoke validation is healthy after resolving `REL-GCP-001`. Safe to proceed to Gate 6.

## Gate 6 - Simulator Validation, 1 Device

Status: PASS

Executed run:

- 1 master node
- 1 camera node
- Duration: 15 minutes
- Target: `https://api.marspotatolab.com`
- Heartbeat interval: 10 seconds
- Sensor interval: 30 seconds
- Image interval: 120 seconds
- Diagnostics interval: 45 seconds
- Command poll interval: 5 seconds

Results:

- Simulator completed without client-side errors.
- Master node status after run: `online`
- Camera node status after run: `online`
- Recent images checked: 14
- Latest image id after run: `1265`
- Timeline events checked: 50
- Timeline event types included:
  - `HEARTBEAT_RECEIVED`
  - `DIAGNOSTICS_RECEIVED`
  - `IMAGE_UPLOAD_STARTED`
  - `IMAGE_CAPTURED`
  - `IMAGE_UPLOADED`
- Cloud Run ERROR logs for active backend revision `plantlab-api-00062-yoh`: none returned for the Gate 6 window.

Gate 6 result:

Single-device simulator validation is healthy. Safe to proceed to Gate 7.

## Gate 7 - Simulator Validation, 5 Devices

Status: PASS

Executed run:

- 5 master nodes
- 1 camera node per master
- Duration: 30 minutes
- Target: `https://api.marspotatolab.com`
- Heartbeat interval: 15 seconds
- Sensor interval: 45 seconds
- Image interval: 180 seconds
- Diagnostics interval: 60 seconds
- Command poll interval: 8 seconds

Results:

- Simulator completed without client-side errors.
- Master/camera registrations completed for 10 total nodes.
- Master status after run: `online`
- Camera nodes after run: 5
- Online camera nodes after run: 5
- Recent images checked: 50
- Image id range checked: `1266` through `1315`
- Unfiltered timeline check returned 100 events and remained responsive.
- Filtered image timeline check returned 20 `IMAGE_UPLOADED` events, latest summary: `Image uploaded #1315 (scheduled)`.
- Cloud Run ERROR logs for active backend revision `plantlab-api-00062-yoh`: none returned for the Gate 7 window.

Notes:

- The unfiltered latest timeline naturally skews toward heartbeat and diagnostics events under multi-node load. Filtering by event type returns image events correctly. This is acceptable for Gate 7, but timeline default-noise reduction remains a future UX/performance improvement area.

Gate 7 result:

Five-device simulator validation is healthy. Safe to proceed to Gate 8.

## Gate 8 - Simulator Validation, 20 Devices

Status: PASS

Executed run:

- 20 master nodes
- 1 camera node per master
- Duration: 30 minutes
- Target: `https://api.marspotatolab.com`
- Scenarios: `unstable_wifi`, `camera_disconnect`, `command_failure`
- Verify backend survival, timeline responsiveness, storage behavior, auth, and absence of event storms or backend errors.

Results:

- Simulator completed without warning-level or error-level output.
- Total simulated nodes: 40
- Final overall device status: `degraded`
- Final primary node status: `degraded`
- Final camera node count: 20
- Final online camera count: 0
- The degraded/offline camera state is expected for the requested `camera_disconnect` and `unstable_wifi` scenario mix.
- Recent images checked: 50
- Image id range checked: `1386` through `1435`
- Filtered image timeline returned 22 `IMAGE_UPLOADED` events.
- Unfiltered timeline check returned 100 events and remained responsive.
- Cloud Run ERROR logs for active backend revision `plantlab-api-00062-yoh`: none returned for the Gate 8 window.

Notes:

- State-change event filters for `CAMERA_NODE_DISCONNECTED` and `WIFI_SIGNAL_DEGRADED` did not return events in this simulator run. The simulator did produce diagnostics/degraded state activity and the backend remained stable, so this does not block Gate 8. It is a simulator scenario fidelity gap to revisit separately if cloud state-change coverage needs to be stricter.

Gate 8 result:

Twenty-device GCP simulator stress passed. Safe to proceed to Gate 9.

## Gate 9 - Simulator OTA Validation

Status: PASS

Executed validation:

- Queue `START_OTA` to a simulator master node.
- Verify command queued/sent/acked/completed.
- Verify simulator OTA status progression and timeline events.
- Verify rollout/manifest path remains healthy under cloud configuration.

Issue found:

- `REL-GCP-002`: Cloud `commands.value` was still `varchar(120)`, causing HTTP 500 when queueing a realistic `START_OTA` payload.

Fix applied:

- Added Alembic migration `20260530_0013_expand_command_value.py`.
- Took a Cloud SQL backup before migration.
- Ran GCP migration job `plantlab-api-migrate-9bnv4` successfully.
- Verified GCP schema:
  - `alembic_version=20260530_0013`
  - `commands_value_length=2000`
- Deployed matching backend revision `plantlab-api-00064-qib`.

Retest results:

- Queued OTA command id: `236`
- Command lifecycle: queued, polled/sent, acked, in progress, completed.
- Simulator OTA statuses observed:
  - `preparing`
  - `downloading`
  - `validating`
  - `installing`
  - `rebooting`
  - `success`
- OTA timeline event filters returned:
  - `OTA_STARTED`: 1
  - `OTA_DOWNLOADING`: 2
  - `OTA_INSTALLING`: 1
  - `OTA_SUCCESS`: 1
  - `OTA_STATE_CHANGED`: 6
  - `OTA_FAILED`: 0
- Cloud Run ERROR logs for active backend revision `plantlab-api-00064-qib`: none returned after retest.

Notes:

- OTA status events currently use OTA message ids as correlation ids rather than the originating `cmd_236` command id. Command and OTA events were both present and correct, but command-to-OTA correlation is weaker than ideal. This is not blocking for Gate 9 because lifecycle and timeline visibility passed.

Gate 9 result:

Simulator OTA validation passed after resolving `REL-GCP-002`. Safe to proceed to Gate 10.

## Gate 10 - Image Upload Validation

Status: PASS

Executed validation:

- Verify image uploads under GCP storage.
- Verify image metadata and signed image URLs.
- Verify image gallery/timeline event readiness.
- Confirm no Cloud Run storage/auth errors after recent stress.

Executed run:

- 5 master nodes
- 1 camera node per master
- Duration: 5 minutes
- Image interval: 30 seconds
- Log level: warning

Results:

- Simulator completed without warning-level or error-level output.
- Recent images checked: 50
- Image id range checked: `1438` through `1487`
- Filtered image timeline returned 30 `IMAGE_UPLOADED` events.
- First three signed GCS image URLs downloaded successfully.
- Downloaded image byte sizes: `3937`, `3931`, `3960`
- Cloud Run ERROR logs for active backend revision `plantlab-api-00064-qib`: none returned for the Gate 10 window.

Gate 10 result:

Image upload validation passed.

## Final Recommendation

Status: A - Safe to proceed to Phase 4: Real ESP32 + Camera on GCP

Phase 3 validated:

- GCP deployment readiness
- Cloud SQL migration path
- Platform and provisioning backend deployment
- Web deployment and `/demo` route
- Authenticated cloud API smoke checks
- GCP simulator baseline
- 5-device simulator load
- 20-device simulator stress with failure scenarios
- Simulator OTA command and OTA_STATUS lifecycle
- GCS image upload, signed URL generation, and image timeline behavior

Resolved during Phase 3:

- `REL-GCP-001`: GCS signed image URL generation on Cloud Run metadata credentials.
- `REL-GCP-002`: Missing cloud migration for `commands.value` length expansion.

Remaining risks:

- OTA status events are present, but OTA event correlation uses OTA message ids rather than the originating command id. This weakens cross-event grouping in the timeline but did not block lifecycle validation.
- Unfiltered timeline views skew toward heartbeat/diagnostics under multi-node simulator load. Event-type filters remain usable.
- Simulator state-change fidelity for `CAMERA_NODE_DISCONNECTED` and `WIFI_SIGNAL_DEGRADED` should be improved if future cloud tests require explicit state-change event assertions.

## Issues

- `REL-GCP-001`: Cloud image signed URL generation failed on Cloud Run metadata credentials. Fixed and retested during Gate 5.
- `REL-GCP-002`: Cloud OTA command payload exceeded `commands.value` length. Fixed with migration and retested during Gate 9.

# Reliability Validation Phase 4 - Real ESP32 + Camera on GCP

Validation phase: Reliability Validation Phase 4 - Real ESP32 + Camera on GCP

Started: 2026-05-30T16:30:46Z

Hardware under validation:

- Master: `pl-esp32-64e0a80af6e8`
- Camera: `pl-cam-1c1df816a398`

## Phase 4 Gate Summary

| Gate | Status | Result |
| --- | --- | --- |
| Gate 1 - Build GCP firmware | PASS WITH CONFIG NOTE | Requested firmware builds passed. The explicit `esp32-gcp` build also passed. Runtime GCP target remains unverified because local `platform_secrets.h` fallback points to the local backend. |
| Gate 2 - Connect devices to GCP | BLOCKED | GCP database records for both hardware ids exist, but last-seen timestamps are stale and firmware versions predate local validation. Devices are not currently reporting to GCP. |

## Phase 4 Gate 1 - Build GCP Firmware

Status: PASS WITH CONFIG NOTE

Executed commands:

- `.venv/bin/pio run -d device/esp32 -e esp32-local`
- `.venv/bin/pio run -d device/esp32 -e camera-platform-test`
- `.venv/bin/pio run -d device/esp32 -e esp32-gcp`

Results:

- `esp32-local`: PASS
  - Firmware artifact: `device/esp32/.pio/build/esp32-local/firmware.bin`
  - RAM: 56,844 bytes / 327,680 bytes
  - Flash: 1,270,425 bytes / 4,718,592 bytes
- `camera-platform-test`: PASS
  - Firmware artifact: `device/esp32/.pio/build/camera-platform-test/firmware.bin`
  - RAM: 50,516 bytes / 327,680 bytes
  - Flash: 1,004,225 bytes / 3,342,336 bytes
- `esp32-gcp`: PASS
  - Firmware artifact: `device/esp32/.pio/build/esp32-gcp/firmware.bin`
  - RAM: 56,844 bytes / 327,680 bytes
  - Flash: 1,270,409 bytes / 4,718,592 bytes

Firmware constants:

- Master firmware version: `0.1.5`
- Master firmware version code: `1005`
- Camera firmware version: `0.1.5`
- Camera firmware version code: `1005`
- Master hardware model expected by backend: `esp32_master`
- Camera hardware model expected by backend: `xiao_esp32s3_camera`

Configuration note:

- `device/esp32/platformio.ini` has a dedicated `esp32-gcp` environment with `PLANTLAB_ENV_LABEL="gcp"`.
- The local, gitignored `device/esp32/include/platform_secrets.h` currently sets the fallback `PLANTLAB_PLATFORM_URL` to `http://192.168.0.55:8000`.
- For GCP hardware validation, the device must either:
  - carry a provisioned runtime config pointing to `https://api.marspotatolab.com`, or
  - be flashed/provisioned with cloud runtime credentials before Gate 2.
- No secret values were recorded in this report.

Gate 1 result:

Firmware builds are healthy. Proceeding to Gate 2 requires confirming or applying cloud runtime provisioning.

## Phase 4 Gate 2 - Connect Devices to GCP

Status: BLOCKED

Executed checks:

- `.venv/bin/pio device list`
- GCP Cloud SQL read-only hardware lookup for:
  - `pl-esp32-64e0a80af6e8`
  - `pl-cam-1c1df816a398`
- GCP Cloud SQL recent timeline lookup for both hardware ids.
- GCP Cloud Run active backend revision check.

Connected serial ports detected locally:

- `/dev/cu.usbmodem1301`
  - USB VID:PID `303A:1001`
  - Serial `E8:F6:0A:A8:E0:64`
  - Likely master node.
- `/dev/cu.usbmodemSN234567892`
  - USB VID:PID `291A:8383`
  - Reported as USB BillBoard.
  - Camera serial identity was not positively confirmed from PlatformIO output.

GCP backend baseline:

- Active backend revision: `plantlab-api-00064-qib`
- GCP device id for the real hardware record: `34`
- GCP device name: `Smart Planter`

GCP hardware records:

| Hardware id | Device id | Node role | Hardware model | Software version | Last seen at | OTA status |
| --- | ---: | --- | --- | --- | --- | --- |
| `pl-esp32-64e0a80af6e8` | 34 | master | `esp32_master` | `0.1.3` | `2026-05-28T13:48:06.186159Z` | idle |
| `pl-cam-1c1df816a398` | 34 | camera | `xiao_esp32s3_camera` | `0.1.4` | `2026-05-29T02:16:52.379187Z` | idle |

Recent GCP timeline evidence:

- Latest camera event for `pl-cam-1c1df816a398`: `reboot` at `2026-05-29T02:11:37Z`.
- Latest master event for `pl-esp32-64e0a80af6e8`: `reboot` at `2026-05-28T06:55:36Z`.
- No current heartbeat or diagnostics events were observed for either node during this validation attempt.

Gate 2 result:

Gate 2 is blocked. The real hardware is not currently reporting to GCP, and the locally connected firmware fallback configuration points to the local backend. Continuing to heartbeat, image upload, command, OTA, or soak gates would produce invalid results.

### Phase 4 Gate 2 Rerun - 2026-05-30T16:35:35Z

Status: BLOCKED

Rerun scope:

- Rebuilt requested firmware targets:
  - `.venv/bin/pio run -d device/esp32 -e esp32-local`
  - `.venv/bin/pio run -d device/esp32 -e camera-platform-test`
- Rebuilt explicit GCP master target:
  - `.venv/bin/pio run -d device/esp32 -e esp32-gcp`
- Queried GCP Cloud SQL for current real hardware state.
- Queried recent GCP timeline events for both real hardware ids.
- Checked active GCP backend revision.

Rerun results:

- `esp32-local`: PASS
- `camera-platform-test`: PASS
- `esp32-gcp`: PASS
- Active backend revision remained `plantlab-api-00064-qib`.
- GCP hardware records were unchanged:
  - Master `pl-esp32-64e0a80af6e8`: firmware `0.1.3`, last seen `2026-05-28T13:48:06.186159Z`.
  - Camera `pl-cam-1c1df816a398`: firmware `0.1.4`, last seen `2026-05-29T02:16:52.379187Z`.
- No current heartbeat or diagnostics events were observed for either node.

Rerun result:

Gate 2 remains blocked. Do not proceed to Gate 3 until both real nodes report current GCP heartbeats and expected firmware versions.

Required operator action before retrying Gate 2:

1. Reprovision the master to GCP from the mobile app, or approve erasing NVS and flashing/provisioning a cloud-target runtime config.
2. Confirm the camera node is connected in a flashable/monitorable serial mode, or reconnect it in a mode that PlatformIO identifies as the XIAO ESP32S3 serial interface.
3. After reprovisioning, rerun the GCP hardware lookup and require both nodes to report current `last_seen_at` timestamps and firmware `0.1.5` before proceeding.

Recommendation:

B - Additional GCP hardware work required before starting the 48-hour GCP soak.

### Phase 4 Gate 2 Recovery - 2026-05-30T17:00:04Z

Status: PASS for hardware recovery / Gate 2 unblock

Recovery scope:

- Audited the physically connected master serial port.
- Verified the master was running firmware `0.1.5` but still using local runtime provisioning:
  - `platform_id=8`
  - `platform=http://192.168.0.55:8000`
  - provisioning env `local`
- Verified `esp32-gcp` only changes the firmware environment label and does not override persisted runtime provisioning in NVS.
- Seeded the master NVS with the existing GCP device runtime configuration for device `34`.
- Reflashed the normal `esp32-gcp` firmware after seeding runtime config.

Root cause:

The master firmware was current enough to run, but its persisted NVS runtime config still pointed at the local backend from local validation. GCP still showed stale firmware/heartbeat records because flashing the GCP firmware environment alone did not replace persisted provisioning credentials or backend URLs.

Recovery actions:

- Wrote GCP runtime config into the master `plantlab` Preferences namespace:
  - `platform_id=34`
  - `platform_url=https://api.marspotatolab.com`
  - provisioning URL set to the GCP provisioning backend
  - existing Wi-Fi credentials retained
  - existing device token for GCP device `34` used
- Reflashed master firmware with:
  - `.venv/bin/pio run -d device/esp32 -e esp32-gcp -t upload --upload-port /dev/cu.usbmodem1301`
- Did not change firmware behavior, backend APIs, onboarding, OTA, or simulator behavior.
- No secret values were recorded in this report.

Post-recovery serial evidence:

- Master booted as:
  - firmware `0.1.5 (1005)`
  - provisioning env `gcp`
  - platform base URL `https://api.marspotatolab.com`
  - platform device id `34`
- Master registered successfully with GCP.
- Master received ESP-NOW camera health reports from the camera node.
- Camera acknowledged a bootstrap capture request with `status=ok`.

GCP hardware records after recovery:

| Hardware id | Device id | Node role | Hardware model | Software version | Last seen at | OTA status | Status |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `pl-esp32-64e0a80af6e8` | 34 | master | `esp32_master` | `0.1.5` | `2026-05-30T16:59:50.751118Z` | idle | online |
| `pl-cam-1c1df816a398` | 34 | camera | `xiao_esp32s3_camera` | `0.1.5` | `2026-05-30T16:59:39.603469Z` | idle | online |

Heartbeat evidence:

- At `2026-05-30T17:00:04Z`, the previous 15 minutes contained:
  - master `HEARTBEAT_RECEIVED`: `53`
  - camera `HEARTBEAT_RECEIVED`: `11`
- Latest master heartbeat payload included:
  - `firmware_version=0.1.5`
  - `hardware_model=esp32_master`
  - `uptime_seconds=514`
  - `wifi_rssi_dbm=-55`
  - `free_heap_bytes=257896`
  - `runtime.ota_status=idle`
  - `runtime.camera_node_status=online`
  - `runtime.time_sync_status=synchronized`
- Latest camera heartbeat payload included:
  - `firmware_version=0.1.5`
  - `node_status=online`
  - `uptime_seconds=495`
  - `wifi_rssi_dbm=-52`

Command validation:

- Queued `REQUEST_DIAGNOSTICS` as command `237`.
  - Result: `completed`
  - Message: `diagnostics heartbeat sent`
- Queued `CAPTURE_IMAGE` as command `238`.
  - Result: `completed`
  - Message: `camera uploaded a new image`
- Timeline showed:
  - `COMMAND_QUEUED`
  - `COMMAND_POLLED`
  - `COMMAND_SENT`
  - `COMMAND_ACKED`
  - `COMMAND_IN_PROGRESS` for capture
  - `COMMAND_COMPLETED`

Image upload evidence:

- New image row:
  - id `1488`
  - source hardware id `pl-cam-1c1df816a398`
  - timestamp `2026-05-30T16:58:22.185726Z`
  - path `gs://plantlab-images-garylu/device-34/20260530_165821_869412_8ce26b95f6364e9aa9b652edc6424877.jpg`
- GCS object check:
  - object exists
  - size `55742` bytes
  - content type `image/jpeg`
- Timeline showed:
  - `IMAGE_UPLOAD_STARTED`
  - `IMAGE_CAPTURED`
  - `IMAGE_UPLOADED`

Diagnostics note:

- Current contract heartbeat runtime fields are visible in the canonical heartbeat timeline and include uptime, RSSI, free heap, firmware version, NTP status, OTA state, and camera-node state.
- The legacy `device_diagnostic_snapshots` rows were still stale after recovery:
  - master snapshot still showed firmware `0.1.3`
  - camera snapshot still showed firmware `0.1.4`
- This was tracked as `REL-GCP-HW-002`.
- Follow-up fix: backend contract heartbeat ingestion now refreshes the legacy snapshot from heartbeat uptime/RSSI/provisioning/last-command fields without emitting a `DIAGNOSTICS_RECEIVED` event per heartbeat. The fix must be deployed before GCP production snapshots refresh from this data.

Gate 2 recovery result:

REL-GCP-HW-001 is resolved for active GCP hardware reporting. Both real nodes are online on GCP, both report firmware `0.1.5`, current heartbeats are visible, command polling works, and one camera image uploaded successfully to GCP storage.

Recommendation:

A - Gate 2 passed for the original recovery blocker. Continue Phase 4 only after acknowledging the diagnostic snapshot freshness caveat above.

### REL-GCP-HW-002 Deployment Validation - 2026-05-30T18:26:39Z

Status: RESOLVED

Backend deployment:

- Built and pushed backend image:
  - `us-central1-docker.pkg.dev/plantlab-493805/plantlab-repo/plantlab-api:1871ea1-20260530181542`
- Deployed no-traffic candidate:
  - revision `plantlab-api-00066-wuf`
  - candidate URL `https://candidate---plantlab-api-efvri7f4ma-uc.a.run.app`
- Candidate health checks:
  - `/health`: PASS
  - `/api/health`: PASS
- Shifted production traffic:
  - `plantlab-api-00066-wuf`: 100%

Snapshot refresh validation:

- Waited for multiple production heartbeats after traffic shift.
- Hardware remained online:

| Hardware id | Node role | Firmware | Last seen at | Status |
| --- | --- | --- | --- | --- |
| `pl-cam-1c1df816a398` | camera | `0.1.5` | `2026-05-30T18:26:39.484857Z` | online |
| `pl-esp32-64e0a80af6e8` | master | `0.1.5` | `2026-05-30T18:26:32.347699Z` | online |

Snapshot rows after deployment:

| Hardware id | Node role | Firmware | RSSI | Uptime | Provisioning | Last command | Updated at |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| `pl-cam-1c1df816a398` | camera | `0.1.5` | `-52` | `5715` | blank | blank | `2026-05-30T18:26:39.484857Z` |
| `pl-esp32-64e0a80af6e8` | master | `0.1.5` | `-51` | `5726` | `NORMAL` | `238 completed` | `2026-05-30T18:26:32.347699Z` |

Conclusion:

`REL-GCP-HW-002` is resolved in production. Contract heartbeat runtime now refreshes `device_diagnostic_snapshots` for both master and camera without adding per-heartbeat `DIAGNOSTICS_RECEIVED` timeline noise.

### Phase 4 Gate 3 - Heartbeat + Diagnostics Observation

Status: BLOCKED on camera NTP state

Observation window:

- Start: `2026-05-30T18:26:56Z`
- End: `2026-05-30T18:41:56Z`
- Backend revision: `plantlab-api-00066-wuf`

Heartbeat continuity:

| Hardware id | Heartbeats | First heartbeat | Latest heartbeat |
| --- | ---: | --- | --- |
| `pl-cam-1c1df816a398` | 20 | `2026-05-30T18:27:24.355243Z` | `2026-05-30T18:41:39.393004Z` |
| `pl-esp32-64e0a80af6e8` | 88 | `2026-05-30T18:27:03.065722Z` | `2026-05-30T18:41:56.551457Z` |

Snapshot state at end of window:

| Hardware id | Node role | Firmware | RSSI | Uptime | Last error | Updated at |
| --- | --- | --- | ---: | ---: | --- | --- |
| `pl-cam-1c1df816a398` | camera | `0.1.5` | `-55` | `6615` | none | `2026-05-30T18:41:39.393004Z` |
| `pl-esp32-64e0a80af6e8` | master | `0.1.5` | `-53` | `6650` | none | `2026-05-30T18:41:56.551457Z` |

Diagnostics/timeline:

- Warning/error/critical diagnostic events during the window: `0`
- Timeline remained readable and contained normal heartbeat events only.
- Cloud Run ERROR logs for `plantlab-api-00066-wuf` during the window: none returned.

NTP state:

- Master: `time_sync_status=synchronized`, `last_ntp_sync_at=2026-05-30T16:46:59Z`
- Camera: `time_sync_status=unsynchronized`

Gate 3 result:

Gate 3 is not fully passed because camera NTP synchronization is not complete. This is tracked separately as `REL-GCP-HW-003`. Do not continue to Phase 4 Gate 4 unless this risk is fixed or explicitly accepted.

### REL-GCP-HW-003 Camera NTP Patch Attempt - 2026-05-30T18:53:56Z

Status: PATCH PUBLISHED, INSTALL NOT CONFIRMED

Root cause confirmed:

- Master firmware includes and starts/services `time_sync_manager`.
- Camera platform firmware included the time sync sources in the PlatformIO build, but its entrypoint did not start or service the manager.

Firmware change:

- Added camera `plantlab::time_sync::begin()` during setup.
- Added camera `plantlab::time_sync::service(g_wifi_ready, now)` in the main loop.
- Bumped camera firmware to `0.1.6 (1006)`.

Build/publish result:

- `camera-platform-test` build passed.
- Published camera-only GCP OTA release:
  - release id `camera-0.1.6-gcp`
  - target hardware id `pl-cam-1c1df816a398`
  - artifact `gs://plantlab-images-garylu/firmware/camera-0.1.6-gcp.bin`
  - size `1007888` bytes
  - SHA-256 `f7a2eb7319a8878c39a8d46b2eed276e259d38f54f96591d00765406c7671953`

Delivery status:

- Camera direct flash was not available from the visible USB ports:
  - `/dev/cu.usbmodem1301` is the Espressif master serial target.
  - `/dev/cu.usbmodemSN234567892` reports as `USB BillBoard`, not a confirmed XIAO ESP32S3 serial target.
- A five-minute GCP poll after publishing showed the camera still on firmware `0.1.5`.
- Latest camera runtime remained `{"time_sync_status": "unsynchronized"}`.
- No camera OTA events appeared during the poll window.

Next required action:

- Power-cycle/reset the camera node so it performs its boot-time OTA manifest check, or connect the camera board directly as an Espressif serial target for flashing.
- After install, rerun Phase 4 Gate 3 for 15 minutes and require camera firmware `0.1.6`, current heartbeats, no warning/error diagnostics, and `runtime.time_sync_status=synchronized`.

### Camera Power-Cycle OTA Monitor - 2026-05-30T19:04:57Z

Status: BLOCKED on camera OTA write failure

The camera was power-cycled and did perform the boot-time OTA manifest check.

Observed OTA lifecycle:

| Event | Time |
| --- | --- |
| `OTA_AVAILABLE` | `2026-05-30T19:04:59Z` |
| `OTA_STARTED` | `2026-05-30T19:05:02Z` |
| `OTA_PREPARING` | `2026-05-30T19:05:02Z` |
| `OTA_DOWNLOADING` | `2026-05-30T19:05:03Z` |
| `OTA_FAILED` | `2026-05-30T19:05:06Z` |

Failure evidence:

- Release: `camera-0.1.6-gcp`
- Target version: `0.1.6`
- Failure reason: `download_failed`
- Failure message: `OTA artifact write failed`
- Camera hardware row after failure:
  - firmware `0.1.5`
  - `ota_status=failed`
  - `ota_error=OTA artifact write failed`
- Latest heartbeat after failure:
  - firmware `0.1.5`
  - `runtime.time_sync_status=unsynchronized`
  - camera remained online

Artifact serving check:

- Direct authenticated fetch of `/api/hardware/ota/artifacts/camera-0.1.6-gcp` returned HTTP 200.
- Downloaded size: `1007888` bytes.
- SHA-256: `f7a2eb7319a8878c39a8d46b2eed276e259d38f54f96591d00765406c7671953`.
- This matches the GCP release metadata.

Result:

The requested monitoring criteria did not pass:

- `0.1.5 -> 0.1.6`: failed, camera remains `0.1.5`
- `OTA_AVAILABLE / OTA_STARTED / OTA_SUCCESS`: partial, `OTA_AVAILABLE` and `OTA_STARTED` observed, `OTA_SUCCESS` not observed
- `time_sync_status=synchronized`: failed, latest runtime remains `unsynchronized`
- `last_ntp_sync_at`: not present

This is tracked as `REL-GCP-HW-004`. Do not rerun the full Gate 3 observation until the camera is direct-flashed or the OTA write failure is fixed.

### REL-GCP-HW-004 Partition and OTA Diagnostic Check

Status: PARTITION SIZE OK, SERIAL LOGS STILL REQUIRED

Partition table:

| Partition | Type | Offset | Size |
| --- | --- | ---: | ---: |
| `app0` | `ota_0` | `0x10000` | `3264K` |
| `app1` | `ota_1` | `0x340000` | `3264K` |

Firmware size comparison:

| Artifact | Size |
| --- | ---: |
| Published `camera-0.1.6-gcp` | `1007888` bytes |
| Current diagnostic camera build | `1009552` bytes |
| Camera OTA slot | `3264K` |

Conclusion:

- The camera OTA partition is large enough.
- The failed OTA is not explained by app slot size.
- The GCP artifact is valid and matches the release checksum.

Firmware diagnostics added for the next serial-backed run:

- `Update.begin()` requested size, result, `Update.getError()`, error string, and free heap.
- HTTP status and content length for the OTA artifact request.
- `Update.write()` requested length, returned length, cumulative bytes, `Update.getError()`, error string, and free heap.
- Periodic OTA write progress/free-heap logs.
- OTA failure reporting now prefers the lower-level write error when available.

Validation:

- `pio run -d device/esp32 -e camera-platform-test` passed after adding the diagnostics.

Remaining blocker:

- The diagnostic firmware is not yet running on the camera.
- The visible USB devices still do not expose the camera as an Espressif serial target.
- To continue, connect the camera board directly as an ESP32-S3 serial device and flash/capture serial logs, or otherwise capture camera serial output during another OTA attempt.
