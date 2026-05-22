#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
STATE_FILE="${PLANTLAB_DEPLOY_STATE:-${SCRIPT_DIR}/.deploy_state}"
INFRA_ENV_DIR="${REPO_ROOT}/platform/infra/env"
DOCKER_DIR="${REPO_ROOT}/platform/infra/docker"
LOADED_ENV_FILES=""

load_env_file() {
  local path="$1"
  if [ -f "$path" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$path"
    set +a
    if [ -z "$LOADED_ENV_FILES" ]; then
      LOADED_ENV_FILES="$path"
    else
      LOADED_ENV_FILES="${LOADED_ENV_FILES},${path}"
    fi
  fi
}

load_env_file "${INFRA_ENV_DIR}/.env"

PROJECT_ID="${PROJECT_ID:-plantlab-493805}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-plantlab-api}"
STAGING_SERVICE_NAME="${STAGING_SERVICE_NAME:-plantlab-api-staging}"
AR_REPO="${AR_REPO:-plantlab-repo}"
DB_INSTANCE="${DB_INSTANCE:-plantlab}"
DB_NAME="${DB_NAME:-plantlab}"
DB_USER="${DB_USER:-plantlab_user}"
BUCKET_NAME="${BUCKET_NAME:-plantlab-images-garylu}"
CLOUD_SQL_CONNECTION_NAME="${CLOUD_SQL_CONNECTION_NAME:-plantlab-493805:us-central1:plantlab}"
RUN_SA="${RUN_SA:-plantlab-run-sa@${PROJECT_ID}.iam.gserviceaccount.com}"
PROVISIONING_URL="${PROVISIONING_URL:-https://plantlab-provision-api-418533861080.us-central1.run.app}"
PLANTLAB_LOCAL_SETUP_URL="${PLANTLAB_LOCAL_SETUP_URL:-http://10.42.0.1:8080/}"
PLANTLAB_APPLE_CLIENT_ID="${PLANTLAB_APPLE_CLIENT_ID:-com.plantlab.mobile}"

usage() {
  cat <<'EOF'
Usage:
  platform/infra/cloud-run/deploy_backend.sh <command>

Scope:
  Backend API only. This deploys the FastAPI Cloud Run service and does not
  deploy the standalone web frontend.

Env loading:
  Reads platform/infra/env/.env. Values exported in the shell still work.
  platform/infra/env/.env.local is reserved for local dev and Docker flows.

Commands:
  print-config       Print non-secret deployment config.
  preflight          Check repo state, GCP resources, secrets, and provisioning health.
  test-local         Run backend tests locally.
  build              Build and push an immutable image to Artifact Registry.
  backup             Create a Cloud SQL backup.
  migrate            Create/update and execute the Alembic Cloud Run migration job.
  deploy-staging     Deploy the image to the staging Cloud Run service.
  deploy-candidate   Deploy a no-traffic production candidate tagged "candidate".
  candidate-url      Print Cloud Run traffic/tag URLs.
  verify-health      Verify /health and /api/health against VERIFY_URL.
  shift-traffic      Shift 100% traffic to candidate. Requires CONFIRM_SHIFT_TRAFFIC=yes.
  rollback           Roll back to ROLLBACK_REVISION.

Required non-secret env for deploy/migrate commands:
  GOOGLE_OAUTH_CLIENT_ID
  PLANTLAB_DEVICE_PLATFORM_URL
  PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX

Optional env:
  PLANTLAB_LOCAL_SETUP_URL, PLANTLAB_APPLE_CLIENT_ID, WEB_ORIGIN, VERIFY_URL, IMAGE_URI, PLANTLAB_DEPLOY_STATE

Secrets are injected by Secret Manager name. Do not export secret values here.
EOF
}

log() {
  printf '[cloud-run] %s\n' "$*"
}

die() {
  printf '[cloud-run] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    die "Set ${name} in ${INFRA_ENV_DIR}/.env or the shell before running this command."
  fi
}

load_state() {
  if [ -f "$STATE_FILE" ]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
  fi
}

save_state() {
  umask 077
  cat >"$STATE_FILE" <<EOF
IMAGE_URI='${IMAGE_URI}'
TAG='${TAG}'
BUILD_COMMIT='$(git -C "$REPO_ROOT" rev-parse --short HEAD)'
EOF
  log "Saved image state to ${STATE_FILE}"
}

require_image_uri() {
  load_state
  if [ -z "${IMAGE_URI:-}" ]; then
    die "IMAGE_URI is not set. Run 'build' first or export IMAGE_URI."
  fi
}

require_runtime_env() {
  require_env GOOGLE_OAUTH_CLIENT_ID
  require_env PLANTLAB_DEVICE_PLATFORM_URL
  require_env PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX
}

runtime_env_vars() {
  require_runtime_env
  printf '%s' "^~^APP_ENV=production~GOOGLE_CLOUD_PROJECT=${PROJECT_ID}~PLANTLAB_STORAGE_BACKEND=gcs~GCS_BUCKET_NAME=${BUCKET_NAME}~PLANTLAB_FIRMWARE_STORAGE_BACKEND=gcs~PLANTLAB_FIRMWARE_BUCKET_NAME=${BUCKET_NAME}~PLANTLAB_FIRMWARE_PREFIX=firmware~DB_NAME=${DB_NAME}~DB_USER=${DB_USER}~CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME}~PLANTLAB_DEV_TOKEN_AUTH_ENABLED=false~PLANTLAB_APPLE_CLIENT_ID=${PLANTLAB_APPLE_CLIENT_ID}~PLANTLAB_PROVISIONING_API_URL=${PROVISIONING_URL}~PLANTLAB_PROVISIONING_PUBLIC_URL=${PROVISIONING_URL}~PLANTLAB_LOCAL_SETUP_URL=${PLANTLAB_LOCAL_SETUP_URL}~PLANTLAB_DEVICE_PLATFORM_URL=${PLANTLAB_DEVICE_PLATFORM_URL}~PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX=${PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX}~PLANTLAB_STANDALONE_MOBILE_SCHEME=plantlab~PLANTLAB_STANDALONE_REFRESH_COOKIE_SAMESITE=lax"
}

migration_env_vars() {
  require_runtime_env
  printf '%s' "^~^APP_ENV=production~GOOGLE_CLOUD_PROJECT=${PROJECT_ID}~PLANTLAB_STORAGE_BACKEND=gcs~GCS_BUCKET_NAME=${BUCKET_NAME}~PLANTLAB_FIRMWARE_STORAGE_BACKEND=gcs~PLANTLAB_FIRMWARE_BUCKET_NAME=${BUCKET_NAME}~PLANTLAB_FIRMWARE_PREFIX=firmware~DB_NAME=${DB_NAME}~DB_USER=${DB_USER}~CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME}~PLANTLAB_DEV_TOKEN_AUTH_ENABLED=false~GOOGLE_OAUTH_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID}~PLANTLAB_APPLE_CLIENT_ID=${PLANTLAB_APPLE_CLIENT_ID}~PLANTLAB_PROVISIONING_API_URL=${PROVISIONING_URL}~PLANTLAB_PROVISIONING_PUBLIC_URL=${PROVISIONING_URL}~PLANTLAB_LOCAL_SETUP_URL=${PLANTLAB_LOCAL_SETUP_URL}~PLANTLAB_DEVICE_PLATFORM_URL=${PLANTLAB_DEVICE_PLATFORM_URL}~PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX=${PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX}~PLANTLAB_STANDALONE_MOBILE_SCHEME=plantlab"
}

secret_bindings() {
  printf '%s' "APP_SECRET_KEY=app-secret-key:latest,DB_PASSWORD=db-password:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest,PLANTLAB_PROVISIONING_SHARED_SECRET=provisioning-shared-secret:latest"
}

service_secret_bindings() {
  printf '%s' "GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,$(secret_bindings)"
}

cmd_print_config() {
  load_state
  cat <<EOF
PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
SERVICE_NAME=${SERVICE_NAME}
STAGING_SERVICE_NAME=${STAGING_SERVICE_NAME}
AR_REPO=${AR_REPO}
DB_INSTANCE=${DB_INSTANCE}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
BUCKET_NAME=${BUCKET_NAME}
CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME}
RUN_SA=${RUN_SA}
PROVISIONING_URL=${PROVISIONING_URL}
PLANTLAB_LOCAL_SETUP_URL=${PLANTLAB_LOCAL_SETUP_URL}
PLANTLAB_APPLE_CLIENT_ID=${PLANTLAB_APPLE_CLIENT_ID}
PLANTLAB_DEVICE_PLATFORM_URL=${PLANTLAB_DEVICE_PLATFORM_URL:-}
PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX=${PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX:-}
GOOGLE_OAUTH_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID:+<set>}
IMAGE_URI=${IMAGE_URI:-}
STATE_FILE=${STATE_FILE}
INFRA_ENV_DIR=${INFRA_ENV_DIR}
LOADED_ENV_FILES=${LOADED_ENV_FILES:-<none>}
EOF
}

cmd_preflight() {
  require_command gcloud
  require_command git
  require_command curl

  log "Setting GCP project: ${PROJECT_ID}"
  gcloud config set project "$PROJECT_ID"

  log "Git state"
  git -C "$REPO_ROOT" status --short
  git -C "$REPO_ROOT" rev-parse --short HEAD

  log "Checking local env files are ignored"
  git -C "$REPO_ROOT" status --short -- .env .env.local platform/infra/env/.env platform/infra/env/.env.local platform/.env platform/backend/.env || true
  git -C "$REPO_ROOT" check-ignore .env .env.local platform/infra/env/.env platform/infra/env/.env.local platform/.env platform/backend/.env || true

  log "Enabled GCP services"
  gcloud services list --enabled \
    --filter='name:(run.googleapis.com OR artifactregistry.googleapis.com OR sqladmin.googleapis.com OR secretmanager.googleapis.com OR cloudbuild.googleapis.com OR storage.googleapis.com)'

  log "Confirming GCP resources"
  gcloud artifacts repositories describe "$AR_REPO" --location "$REGION"
  gcloud sql instances describe "$DB_INSTANCE"
  gcloud sql databases describe "$DB_NAME" --instance "$DB_INSTANCE"
  gcloud storage buckets describe "gs://${BUCKET_NAME}"
  gcloud iam service-accounts describe "$RUN_SA"

  log "Confirming Secret Manager secrets exist"
  gcloud secrets describe db-password
  gcloud secrets describe app-secret-key
  gcloud secrets describe google-oauth-client-id
  gcloud secrets describe google-oauth-client-secret
  gcloud secrets describe provisioning-shared-secret

  log "Checking provisioning service health"
  curl -fsS "${PROVISIONING_URL}/health"
  printf '\n'
}

cmd_test_local() {
  log "Running backend tests"
  (
    cd "$REPO_ROOT/platform/backend"
    env \
      -u APP_ENV \
      -u APP_SECRET_KEY \
      -u CLOUD_SQL_CONNECTION_NAME \
      -u DATABASE_URL \
      -u DB_HOST \
      -u DB_PASSWORD \
      -u GCS_BUCKET_NAME \
      -u GOOGLE_CLIENT_ID \
      -u GOOGLE_CLIENT_SECRET \
      -u GOOGLE_OAUTH_CLIENT_ID \
      -u GOOGLE_OAUTH_CLIENT_SECRET \
      -u PLANTLAB_DATABASE_URL \
      -u PLANTLAB_DEVICE_PLATFORM_URL \
      -u PLANTLAB_DEV_TOKEN_AUTH_ENABLED \
      -u PLANTLAB_PROVISIONING_API_URL \
      -u PLANTLAB_PROVISIONING_PUBLIC_URL \
      -u PLANTLAB_PROVISIONING_SHARED_SECRET \
      -u PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX \
      -u PLANTLAB_STORAGE_BACKEND \
      PLANTLAB_SKIP_DOTENV=1 \
      ../../.venv/bin/python -m pytest tests
  )
}

cmd_build() {
  require_command gcloud
  require_command git
  TAG="${TAG:-$(git -C "$REPO_ROOT" rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)}"
  IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}:${TAG}"

  log "Building image: ${IMAGE_URI}"
  gcloud auth configure-docker "${REGION}-docker.pkg.dev"
  gcloud builds submit "$REPO_ROOT" \
    --config "${DOCKER_DIR}/cloudbuild.platform.yaml" \
    --substitutions "_IMAGE_URI=${IMAGE_URI}"
  save_state
}

cmd_backup() {
  require_command gcloud
  log "Creating Cloud SQL backup for ${DB_INSTANCE}"
  gcloud sql backups create --instance "$DB_INSTANCE"
}

cmd_migrate() {
  require_command gcloud
  require_image_uri
  local migration_job="${MIGRATION_JOB:-plantlab-api-migrate}"
  local job_action

  if gcloud run jobs describe "$migration_job" --region "$REGION" >/dev/null 2>&1; then
    job_action=update
  else
    job_action=create
  fi

  log "${job_action} migration job ${migration_job} using ${IMAGE_URI}"
  gcloud run jobs "$job_action" "$migration_job" \
    --image "$IMAGE_URI" \
    --region "$REGION" \
    --service-account "$RUN_SA" \
    --set-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
    --tasks 1 \
    --max-retries 0 \
    --command alembic \
    --args upgrade,head \
    --set-env-vars "$(migration_env_vars)" \
    --set-secrets "$(secret_bindings)"

  log "Executing migration job ${migration_job}"
  gcloud run jobs execute "$migration_job" --region "$REGION" --wait
}

cmd_deploy_staging() {
  require_command gcloud
  require_image_uri
  log "Deploying staging service ${STAGING_SERVICE_NAME} using ${IMAGE_URI}"
  gcloud run deploy "$STAGING_SERVICE_NAME" \
    --image "$IMAGE_URI" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --service-account "$RUN_SA" \
    --add-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
    --set-env-vars "$(runtime_env_vars)" \
    --set-secrets "$(service_secret_bindings)"
}

cmd_deploy_candidate() {
  require_command gcloud
  require_image_uri
  log "Deploying no-traffic candidate for ${SERVICE_NAME} using ${IMAGE_URI}"
  gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URI" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --service-account "$RUN_SA" \
    --add-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
    --no-traffic \
    --tag candidate \
    --set-env-vars "$(runtime_env_vars)" \
    --set-secrets "$(service_secret_bindings)"
  cmd_candidate_url
}

cmd_candidate_url() {
  require_command gcloud
  gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --flatten='status.traffic[]' \
    --format='table(status.traffic.tag,status.traffic.url,status.traffic.percent,status.traffic.revisionName)'
}

cmd_verify_health() {
  require_command curl
  require_env VERIFY_URL
  log "Checking ${VERIFY_URL}/health"
  curl -fsS "${VERIFY_URL}/health"
  printf '\n'
  log "Checking ${VERIFY_URL}/api/health"
  curl -fsS "${VERIFY_URL}/api/health"
  printf '\n'
}

cmd_shift_traffic() {
  require_command gcloud
  if [ "${CONFIRM_SHIFT_TRAFFIC:-}" != "yes" ]; then
    die "Set CONFIRM_SHIFT_TRAFFIC=yes to shift production traffic."
  fi
  log "Shifting 100% traffic to candidate tag for ${SERVICE_NAME}"
  gcloud run services update-traffic "$SERVICE_NAME" \
    --region "$REGION" \
    --to-tags candidate=100
}

cmd_rollback() {
  require_command gcloud
  require_env ROLLBACK_REVISION
  log "Rolling back ${SERVICE_NAME} to revision ${ROLLBACK_REVISION}"
  gcloud run services update-traffic "$SERVICE_NAME" \
    --region "$REGION" \
    --to-revisions "${ROLLBACK_REVISION}=100"
}

main() {
  local command="${1:-}"
  case "$command" in
    print-config) cmd_print_config ;;
    preflight) cmd_preflight ;;
    test-local) cmd_test_local ;;
    build) cmd_build ;;
    backup) cmd_backup ;;
    migrate) cmd_migrate ;;
    deploy-staging) cmd_deploy_staging ;;
    deploy-candidate) cmd_deploy_candidate ;;
    candidate-url) cmd_candidate_url ;;
    verify-health) cmd_verify_health ;;
    shift-traffic) cmd_shift_traffic ;;
    rollback) cmd_rollback ;;
    ""|-h|--help|help) usage ;;
    *) usage; die "Unknown command: ${command}" ;;
  esac
}

main "$@"
