# PlantLab Cloud Run Deployment Runbook

This runbook prepares and executes the first controlled GCP production
deployment for the PlantLab platform backend API. It is intentionally manual:
verify every preflight item, deploy a staging or no-traffic candidate first,
run migrations deliberately, then shift production traffic only after approval.

This does not deploy the standalone web frontend. The web app should have a
separate deployment script once the production hosting target is chosen.

Do not paste secrets into shell history, logs, issue comments, or reports. Store
secret values in Secret Manager and inject them into Cloud Run by secret name.

## Deployment Targets

- Backend entrypoint: `platform/backend/app/main.py`
- Container entrypoint: `platform/infra/docker/Dockerfile.platform`
- Runtime: Cloud Run service `plantlab-api`
- Optional staging service: `plantlab-api-staging`
- Region: `us-central1`
- Project: `plantlab-493805`
- Artifact Registry repo: `plantlab-repo`
- Cloud SQL instance: `plantlab`
- Cloud SQL database: `plantlab`
- Cloud SQL user: `plantlab_user`
- Cloud SQL connection name: `plantlab-493805:us-central1:plantlab`
- GCS image bucket: `plantlab-images-garylu`
- Runtime service account:
  `plantlab-run-sa@plantlab-493805.iam.gserviceaccount.com`

Confirm these values against live GCP before deployment.

## Manual Approval Gates

Deployment must pause for approval at these points:

- Before creating or changing any GCP resource.
- Before building and pushing the release image.
- Before running database migrations.
- Before deploying a production candidate.
- Before shifting any production traffic.
- Before changing custom domain mappings or client production API URLs.

## Deployment Helper Script

The deployment commands below are also available as subcommands in:

```bash
platform/infra/cloud-run/deploy_backend.sh
platform/infra/cloud-run/deploy_provisioning_backend.sh
```

The helpers keep deployment staged. They do not shift traffic unless
`CONFIRM_SHIFT_TRAFFIC=yes` is set explicitly.

PlantLab has two backend Cloud Run services:

- `plantlab-provision-api`: Express provisioning service for setup-code,
  BLE claim-token, and device registration during onboarding.
- `plantlab-api`: FastAPI platform service for auth, dashboard data,
  hardware readings, commands, images, and the legacy backend web routes.

Deploy provisioning contract changes before platform API changes that depend on
them. This prevents the platform API from sending a newer provisioning payload
to an older provisioning service.

Typical first production flow:

```bash
$EDITOR platform/infra/env/.env

platform/infra/cloud-run/deploy_backend.sh print-config
platform/infra/cloud-run/deploy_backend.sh preflight
platform/infra/cloud-run/deploy_backend.sh test-local

platform/infra/cloud-run/deploy_provisioning_backend.sh print-config
platform/infra/cloud-run/deploy_provisioning_backend.sh preflight
platform/infra/cloud-run/deploy_provisioning_backend.sh test-local
platform/infra/cloud-run/deploy_provisioning_backend.sh build
platform/infra/cloud-run/deploy_provisioning_backend.sh deploy-candidate
platform/infra/cloud-run/deploy_provisioning_backend.sh candidate-url

platform/infra/cloud-run/deploy_backend.sh build
platform/infra/cloud-run/deploy_backend.sh backup
platform/infra/cloud-run/deploy_backend.sh migrate
platform/infra/cloud-run/deploy_backend.sh deploy-candidate
platform/infra/cloud-run/deploy_backend.sh candidate-url
```

The deployment helper loads only `platform/infra/env/.env`. Keep
`platform/infra/env/.env.local` for local Docker and direct development flows,
not deployment.

Minimum non-secret values for `platform/infra/env/.env`:

```bash
GOOGLE_OAUTH_CLIENT_ID="<oauth-client-id>"
PLANTLAB_LOCAL_SETUP_URL="http://10.42.0.1:8080/"
PLANTLAB_DEVICE_PLATFORM_URL="<production-api-url-or-custom-domain>"
PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX="^https://(marspotatolab\.com|app\.marspotatolab\.com)$"
```

The standalone web origin regex must include every production web origin that
can initiate browser auth. If root web traffic is served from
`https://marspotatolab.com`, the backend must allow that origin or Google login
will fail with `invalid_return_to`.

After copying the candidate URL from `candidate-url`:

```bash
export VERIFY_URL="<candidate-tag-url>"
platform/infra/cloud-run/deploy_backend.sh verify-health
```

For the provisioning candidate:

```bash
export VERIFY_URL="<provisioning-candidate-tag-url>"
platform/infra/cloud-run/deploy_provisioning_backend.sh verify-health
```

Only after the full manual verification checklist passes:

```bash
CONFIRM_SHIFT_TRAFFIC=yes platform/infra/cloud-run/deploy_provisioning_backend.sh shift-traffic
CONFIRM_SHIFT_TRAFFIC=yes platform/infra/cloud-run/deploy_backend.sh shift-traffic
```

Rollback requires the previous stable revision name:

```bash
gcloud run revisions list --service plantlab-provision-api --region us-central1
ROLLBACK_REVISION="<previous-stable-revision>" platform/infra/cloud-run/deploy_provisioning_backend.sh rollback

gcloud run revisions list --service plantlab-api --region us-central1
ROLLBACK_REVISION="<previous-stable-revision>" platform/infra/cloud-run/deploy_backend.sh rollback
```

## Preflight

Set non-secret shell variables for the deployment session:

```bash
PROJECT_ID=plantlab-493805
REGION=us-central1
SERVICE_NAME=plantlab-api
STAGING_SERVICE_NAME=plantlab-api-staging
AR_REPO=plantlab-repo
DB_INSTANCE=plantlab
DB_NAME=plantlab
DB_USER=plantlab_user
BUCKET_NAME=plantlab-images-garylu
CLOUD_SQL_CONNECTION_NAME=plantlab-493805:us-central1:plantlab
RUN_SA=plantlab-run-sa@${PROJECT_ID}.iam.gserviceaccount.com
PROVISIONING_URL=https://plantlab-provision-api-418533861080.us-central1.run.app
```

Confirm the release commit and current worktree:

```bash
git status --short
git rev-parse --short HEAD
```

Confirm real secrets are not tracked. Runtime/deployment env files should live
under `platform/infra/env/`; root `.env` and `.env.local` may exist only as
local compatibility symlinks:

```bash
git status --short -- .env .env.local platform/infra/env/.env platform/infra/env/.env.local platform/.env platform/backend/.env
git check-ignore .env .env.local platform/infra/env/.env platform/infra/env/.env.local platform/.env platform/backend/.env
```

Confirm required APIs are enabled or explicitly approve enabling them:

```bash
gcloud services list --enabled \
  --filter='name:(run.googleapis.com OR artifactregistry.googleapis.com OR sqladmin.googleapis.com OR secretmanager.googleapis.com OR cloudbuild.googleapis.com OR storage.googleapis.com)'
```

Confirm GCP resources:

```bash
gcloud config set project "$PROJECT_ID"
gcloud artifacts repositories describe "$AR_REPO" --location "$REGION"
gcloud sql instances describe "$DB_INSTANCE"
gcloud sql databases describe "$DB_NAME" --instance "$DB_INSTANCE"
gcloud storage buckets describe "gs://${BUCKET_NAME}"
gcloud iam service-accounts describe "$RUN_SA"
```

Confirm the provisioning service is reachable:

```bash
curl -fsS "${PROVISIONING_URL}/health"
```

Run the local backend test suite before building:

```bash
cd platform/backend
../../.venv/bin/python -m pytest tests
```

## IAM

Grant the Cloud Run runtime service account only the permissions it needs:

- Cloud SQL Client on the project or Cloud SQL resource.
- Secret accessor on the specific PlantLab secrets listed below.
- Bucket-scoped object permissions for `gs://plantlab-images-garylu`.

Prefer bucket-level storage roles over project-wide storage admin. If read and
write access are both required through the backend image proxy, use the narrowest
bucket-level role that satisfies the workflow.

## Secrets

Create or update these Secret Manager secrets without printing their values:

- `db-password` -> `DB_PASSWORD`
- `app-secret-key` -> `APP_SECRET_KEY`
- `google-oauth-client-id` -> `GOOGLE_OAUTH_CLIENT_ID`
- `google-oauth-client-secret` -> `GOOGLE_OAUTH_CLIENT_SECRET`
- `provisioning-shared-secret` ->
  `PLANTLAB_PROVISIONING_SHARED_SECRET`

Confirm the secrets exist:

```bash
gcloud secrets describe db-password
gcloud secrets describe app-secret-key
gcloud secrets describe google-oauth-client-id
gcloud secrets describe google-oauth-client-secret
gcloud secrets describe provisioning-shared-secret
```

Grant access to the runtime service account on each secret:

```bash
for SECRET in \
  db-password \
  app-secret-key \
  google-oauth-client-id \
  google-oauth-client-secret \
  provisioning-shared-secret
do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member "serviceAccount:${RUN_SA}" \
    --role roles/secretmanager.secretAccessor
done
```

## Runtime Environment

Required non-secret Cloud Run environment variables:

```bash
APP_ENV=production
GOOGLE_CLOUD_PROJECT=plantlab-493805
PLANTLAB_STORAGE_BACKEND=gcs
GCS_BUCKET_NAME=plantlab-images-garylu
PLANTLAB_FIRMWARE_STORAGE_BACKEND=gcs
PLANTLAB_FIRMWARE_BUCKET_NAME=plantlab-images-garylu
PLANTLAB_FIRMWARE_PREFIX=firmware
DB_NAME=plantlab
DB_USER=plantlab_user
CLOUD_SQL_CONNECTION_NAME=plantlab-493805:us-central1:plantlab
PLANTLAB_DEV_TOKEN_AUTH_ENABLED=false
GOOGLE_OAUTH_CLIENT_ID=<oauth-client-id>
PLANTLAB_PROVISIONING_API_URL=https://plantlab-provision-api-418533861080.us-central1.run.app
PLANTLAB_PROVISIONING_PUBLIC_URL=https://plantlab-provision-api-418533861080.us-central1.run.app
PLANTLAB_LOCAL_SETUP_URL=http://10.42.0.1:8080/
PLANTLAB_DEVICE_PLATFORM_URL=<production-api-or-custom-domain>
PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX=<exact-production-web-origin-regex>
PLANTLAB_STANDALONE_MOBILE_SCHEME=plantlab
PLANTLAB_STANDALONE_REFRESH_COOKIE_SAMESITE=lax
```

Field meanings and where to find them:

- `PLANTLAB_LOCAL_SETUP_URL`: the ESP32 SoftAP setup page URL used during
  Wi-Fi onboarding. For the current firmware this should stay
  `http://10.42.0.1:8080/` unless the ESP32 setup AP IP or port changes.
- `PLANTLAB_DEVICE_PLATFORM_URL`: the platform API URL written into device
  provisioning payloads. ESP32 hardware uses this URL for readings, heartbeats,
  commands, and image upload after onboarding. Use the final production backend
  URL that devices can reach, preferably the custom API domain. If no custom
  domain is configured yet, use the Cloud Run service URL from:

  ```bash
  gcloud run services describe plantlab-api \
    --region us-central1 \
    --format='value(status.url)'
  ```

  For a no-traffic candidate, verify with the candidate tag URL first, but use
  the stable production service URL or custom domain for device provisioning
  once traffic is shifted.
- `PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX`: the exact allowed browser origin for
  the standalone web frontend. This controls production CORS/auth refresh
  access. Get the origin from the deployed web app URL, for example
  `https://app.example.com`, then anchor and escape it as a regex:

  ```bash
  export PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX='^https://app\.example\.com$'
  ```

  Do not use `.*` for production unless a temporary exception is explicitly
  approved.

Do not set `DATABASE_URL` for Cloud Run when using the Cloud SQL socket. The
backend builds its PostgreSQL URL from `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and
`CLOUD_SQL_CONNECTION_NAME`.

## OAuth And CORS

Before deployment, confirm the Google OAuth client includes callback URLs for
the selected API domain:

```text
https://<api-domain>/auth/callback
https://<api-domain>/api/auth/google/callback
```

Set `PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX` to the exact production web origin.
Do not use a broad regex such as `.*` unless a temporary exception has been
approved and documented.

For mobile production builds, confirm:

```bash
EXPO_PUBLIC_API_BASE_URL=<production-api-url>
EXPO_PUBLIC_AUTH_MODE=production
EXPO_PUBLIC_ENABLE_DEV_AUTH=false
EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false
```

## Production OTA Publishing

Production OTA firmware artifacts are backend-owned files in GCS. The platform
API serves them through `/api/hardware/ota/artifacts/{release_id}` after the
device authenticates with its device token.

The production path is:

1. build the firmware image
2. upload the `.bin` file to `gs://plantlab-images-garylu/firmware/`
3. run a Cloud Run job using the deployed backend image
4. upsert one row in `firmware_releases` with a `gs://...` artifact path,
   SHA256, size, node role, hardware model, and version code

Use the helper script instead of manually editing production SQL:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/ota_release.py publish-gcp \
  --node camera \
  --version 0.1.5 \
  --build
```

The helper creates or updates the Cloud Run job
`plantlab-firmware-release-publish`. That job runs:

```bash
python -m app.ops.publish_firmware_release
```

Important: deploy the backend image that contains this module before running
`publish-gcp`. Use `--dry-run` to inspect the upload and job commands before
changing GCP.

## Build Image

Use immutable image tags for rollback. Do not deploy `latest`.

```bash
TAG="$(git rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}:${TAG}"

gcloud auth configure-docker "${REGION}-docker.pkg.dev"
gcloud builds submit . \
  --config platform/infra/docker/cloudbuild.platform.yaml \
  --substitutions "_IMAGE_URI=${IMAGE_URI}"
```

Record `IMAGE_URI` in the release notes after the build completes.

## Deploy Staging

Deploy staging first when a staging service is approved:

```bash
gcloud run deploy "$STAGING_SERVICE_NAME" \
  --image "$IMAGE_URI" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --service-account "$RUN_SA" \
  --add-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
  --set-env-vars APP_ENV=production,GOOGLE_CLOUD_PROJECT="$PROJECT_ID",PLANTLAB_STORAGE_BACKEND=gcs,GCS_BUCKET_NAME="$BUCKET_NAME",DB_NAME="$DB_NAME",DB_USER="$DB_USER",CLOUD_SQL_CONNECTION_NAME="$CLOUD_SQL_CONNECTION_NAME",PLANTLAB_DEV_TOKEN_AUTH_ENABLED=false,PLANTLAB_PROVISIONING_API_URL="$PROVISIONING_URL",PLANTLAB_PROVISIONING_PUBLIC_URL="$PROVISIONING_URL",PLANTLAB_LOCAL_SETUP_URL="$PLANTLAB_LOCAL_SETUP_URL",PLANTLAB_DEVICE_PLATFORM_URL="$PLANTLAB_DEVICE_PLATFORM_URL",PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX="$PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX",PLANTLAB_STANDALONE_MOBILE_SCHEME=plantlab,PLANTLAB_STANDALONE_REFRESH_COOKIE_SAMESITE=lax \
  --set-secrets GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,APP_SECRET_KEY=app-secret-key:latest,DB_PASSWORD=db-password:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest,PLANTLAB_PROVISIONING_SHARED_SECRET=provisioning-shared-secret:latest
```

## Database Migrations

The backend skips automatic table creation in production. Run Alembic before
traffic is shifted.

Before migration:

- Take a Cloud SQL backup.
- Inspect whether `alembic_version` exists.
- If the database is empty or already managed by Alembic, run `upgrade head`.
- If tables already exist without Alembic history, stop and reconcile schema
  state before running migrations.
- Confirm provisioning tables are present or initialized by the provisioning
  service if the provisioning service shares this database.

Use a Cloud Run Job with the same image, Cloud SQL attachment, service account,
environment variables, and secrets as the API service. The migration job keeps
`GOOGLE_OAUTH_CLIENT_ID` as a literal env var to match the existing job; the
Cloud Run API service uses the `google-oauth-client-id` secret.

```bash
MIGRATION_JOB=plantlab-api-migrate

gcloud run jobs describe "$MIGRATION_JOB" --region "$REGION" >/dev/null 2>&1
if [ "$?" -eq 0 ]; then
  JOB_ACTION=update
else
  JOB_ACTION=create
fi

gcloud run jobs "$JOB_ACTION" "$MIGRATION_JOB" \
  --image "$IMAGE_URI" \
  --region "$REGION" \
  --service-account "$RUN_SA" \
  --set-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
  --tasks 1 \
  --max-retries 0 \
  --command alembic \
  --args upgrade,head \
  --set-env-vars APP_ENV=production,GOOGLE_CLOUD_PROJECT="$PROJECT_ID",PLANTLAB_STORAGE_BACKEND=gcs,GCS_BUCKET_NAME="$BUCKET_NAME",DB_NAME="$DB_NAME",DB_USER="$DB_USER",CLOUD_SQL_CONNECTION_NAME="$CLOUD_SQL_CONNECTION_NAME",PLANTLAB_DEV_TOKEN_AUTH_ENABLED=false,GOOGLE_OAUTH_CLIENT_ID="$GOOGLE_OAUTH_CLIENT_ID",PLANTLAB_PROVISIONING_API_URL="$PROVISIONING_URL",PLANTLAB_PROVISIONING_PUBLIC_URL="$PROVISIONING_URL",PLANTLAB_LOCAL_SETUP_URL="$PLANTLAB_LOCAL_SETUP_URL",PLANTLAB_DEVICE_PLATFORM_URL="$PLANTLAB_DEVICE_PLATFORM_URL",PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX="$PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX",PLANTLAB_STANDALONE_MOBILE_SCHEME=plantlab \
  --set-secrets APP_SECRET_KEY=app-secret-key:latest,DB_PASSWORD=db-password:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest,PLANTLAB_PROVISIONING_SHARED_SECRET=provisioning-shared-secret:latest

gcloud run jobs execute "$MIGRATION_JOB" --region "$REGION" --wait
```

## Deploy Production Candidate

Deploy the production revision with no traffic first:

```bash
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URI" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --service-account "$RUN_SA" \
  --add-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
  --no-traffic \
  --tag candidate \
  --set-env-vars APP_ENV=production,GOOGLE_CLOUD_PROJECT="$PROJECT_ID",PLANTLAB_STORAGE_BACKEND=gcs,GCS_BUCKET_NAME="$BUCKET_NAME",DB_NAME="$DB_NAME",DB_USER="$DB_USER",CLOUD_SQL_CONNECTION_NAME="$CLOUD_SQL_CONNECTION_NAME",PLANTLAB_DEV_TOKEN_AUTH_ENABLED=false,PLANTLAB_PROVISIONING_API_URL="$PROVISIONING_URL",PLANTLAB_PROVISIONING_PUBLIC_URL="$PROVISIONING_URL",PLANTLAB_LOCAL_SETUP_URL="$PLANTLAB_LOCAL_SETUP_URL",PLANTLAB_DEVICE_PLATFORM_URL="$PLANTLAB_DEVICE_PLATFORM_URL",PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX="$PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX",PLANTLAB_STANDALONE_MOBILE_SCHEME=plantlab,PLANTLAB_STANDALONE_REFRESH_COOKIE_SAMESITE=lax \
  --set-secrets GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,APP_SECRET_KEY=app-secret-key:latest,DB_PASSWORD=db-password:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest,PLANTLAB_PROVISIONING_SHARED_SECRET=provisioning-shared-secret:latest
```

List the tagged URLs and use the candidate URL for verification before traffic
shift. The normal service URL may still route to the previous stable revision.

```bash
gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --format='table(status.trafficStatuses.tag,status.trafficStatuses.url,status.trafficStatuses.percent)'

VERIFY_URL=<candidate-tag-url>
```

## Verification

For staging verification, set `VERIFY_URL` to the staging service URL:

```bash
VERIFY_URL="$(gcloud run services describe "$STAGING_SERVICE_NAME" \
  --region "$REGION" \
  --format='value(status.url)')"
```

Health check:

```bash
curl -fsS "${VERIFY_URL}/health"
curl -fsS "${VERIFY_URL}/api/health"
```

CORS preflight from the approved web origin:

```bash
curl -i -X OPTIONS "${VERIFY_URL}/api/auth/refresh" \
  -H "Origin: ${WEB_ORIGIN}" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization"
```

OAuth start:

```bash
curl -I "${VERIFY_URL}/api/auth/google/start?client=web&return_to=${WEB_ORIGIN_ENCODED}%2Flogin%3Fauth%3Dcomplete"
```

Browser Google auth:

1. Open the Google auth start URL in a browser.
2. Complete Google sign-in with an approved production test account.
3. Confirm the browser returns to the approved web origin.
4. Confirm the authenticated session works:

```bash
curl -fsS "${VERIFY_URL}/api/me" \
  -H "Authorization: Bearer ${WEB_ACCESS_TOKEN}"
```

Expected result: `/api/me` returns the authenticated user for the production
test account. If the web app uses secure refresh cookies instead of exposing an
access token, verify `/api/me` from the authenticated browser session.

Mobile auth:

1. Build or launch the mobile app with production API settings.
2. Confirm `EXPO_PUBLIC_API_BASE_URL` points at `VERIFY_URL` or the approved
   production API domain.
3. Complete Google sign-in from the app.
4. Confirm the OAuth callback returns through `plantlab://auth/callback`.
5. Confirm the mobile app creates a production session and can load `/api/me`.

Hardware readings and command polling. Read the device token silently and do not
paste it into logs:

```bash
read -s DEVICE_TOKEN
.venv/bin/python platform/infra/scripts/hardware_simulator.py \
  --base-url "$VERIFY_URL" \
  --device-token "$DEVICE_TOKEN" \
  --hardware-device-id "$HARDWARE_DEVICE_ID"
```

This script verifies the implemented hardware API contract:

- `POST /api/hardware/readings`
- `GET /api/hardware/commands/pending`
- `POST /api/hardware/commands/{command_id}/result`

Legacy device data and command smoke checks:

These checks explicitly cover:

- `POST /api/data`
- `GET /api/devices/{device_id}/commands/pending`
- `POST /api/devices/{device_id}/commands/{command_id}/ack`

```bash
curl -fsS -X POST "${VERIFY_URL}/api/data" \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: ${DEVICE_TOKEN}" \
  -d '{"device_id":'"${DEVICE_ID}"',"hardware_device_id":"'"${HARDWARE_DEVICE_ID}"'","moisture":42.5,"temperature":22.2,"humidity":51.0,"light_on":false,"pump_on":false,"pump_status":"not_needed"}'

curl -fsS "${VERIFY_URL}/api/devices/${DEVICE_ID}/commands/pending" \
  -H "X-Device-Token: ${DEVICE_TOKEN}"
```

If a pending command is returned, acknowledge only the command created for this
smoke test:

```bash
curl -fsS -X POST "${VERIFY_URL}/api/devices/${DEVICE_ID}/commands/${COMMAND_ID}/ack" \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: ${DEVICE_TOKEN}" \
  -d '{"status":"completed","message":"production smoke test","light_on":false,"pump_on":false}'
```

Expected result: `POST /api/data` succeeds, command polling returns a JSON list,
and the ack endpoint succeeds for a known smoke-test command.

Heartbeat:

```bash
curl -fsS -X POST "${VERIFY_URL}/api/hardware/heartbeat" \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: ${DEVICE_TOKEN}" \
  -d '{"hardware_device_id":"'"${HARDWARE_DEVICE_ID}"'","status":"online","light_on":false,"pump_on":false,"message":"production smoke test"}'
```

Image upload:

```bash
curl -fsS -X POST "${VERIFY_URL}/api/image" \
  -H "X-Device-Token: ${DEVICE_TOKEN}" \
  -F "device_id=${DEVICE_ID}" \
  -F "source_hardware_device_id=${HARDWARE_DEVICE_ID}" \
  -F "file=@/path/to/test-image.jpg;type=image/jpeg"
```

Then verify the object exists in the GCS bucket and authenticated image content
can be read through the backend image proxy.

Check recent Cloud Run logs and confirm no secrets, OAuth secret values, device
tokens, Wi-Fi credentials, or repeated startup failures appear:

```bash
gcloud logs read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
  --limit=100
```

## Traffic Shift

After candidate verification and manual approval, shift traffic:

```bash
gcloud run services update-traffic "$SERVICE_NAME" \
  --region "$REGION" \
  --to-tags candidate=100
```

If an existing stable production revision is serving traffic, consider a staged
split first:

```bash
gcloud run services update-traffic "$SERVICE_NAME" \
  --region "$REGION" \
  --to-tags candidate=10 \
  --to-revisions <stable-revision>=90
```

## Rollback

List revisions:

```bash
gcloud run revisions list \
  --service "$SERVICE_NAME" \
  --region "$REGION"
```

Rollback traffic to the previous stable revision:

```bash
gcloud run services update-traffic "$SERVICE_NAME" \
  --region "$REGION" \
  --to-revisions <previous-stable-revision>=100
```

Application rollback does not roll back database schema changes. If migration
rollback is needed, use the pre-migration Cloud SQL backup or an explicitly
reviewed Alembic downgrade plan.

## Release Checklist

- [ ] GCP project, region, database, bucket, Artifact Registry repo, and service
      account confirmed.
- [ ] Runtime service account IAM reviewed for least privilege.
- [ ] Secret Manager secrets created or updated without printing values.
- [ ] OAuth redirect URLs configured for the final API domain.
- [ ] Production web origin and CORS regex approved.
- [ ] Cloud SQL backup completed.
- [ ] Migration strategy approved after schema inspection.
- [ ] Staging or production candidate deployed before traffic shift.
- [ ] Health, CORS, OAuth, hardware, heartbeat, image upload, and logs verified.
- [ ] Mobile app production API URL verified.
- [ ] Rollback owner and rollback command agreed before traffic shift.
- [ ] Release Agent remains read-only and writes `release_report.md`.
