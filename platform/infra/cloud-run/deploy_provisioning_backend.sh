#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
STATE_FILE="${PLANTLAB_PROVISIONING_DEPLOY_STATE:-${SCRIPT_DIR}/.provisioning_deploy_state}"
INFRA_ENV_DIR="${REPO_ROOT}/platform/infra/env"
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
SERVICE_NAME="${PROVISIONING_SERVICE_NAME:-plantlab-provision-api}"
AR_REPO="${AR_REPO:-plantlab-repo}"
DB_INSTANCE="${DB_INSTANCE:-plantlab}"
DB_NAME="${DB_NAME:-plantlab}"
DB_USER="${DB_USER:-plantlab_user}"
CLOUD_SQL_CONNECTION_NAME="${CLOUD_SQL_CONNECTION_NAME:-plantlab-493805:us-central1:plantlab}"
RUN_SA="${RUN_SA:-plantlab-run-sa@${PROJECT_ID}.iam.gserviceaccount.com}"
PLANTLAB_LOCAL_SETUP_URL="${PLANTLAB_LOCAL_SETUP_URL:-http://10.42.0.1:8080/}"
PLANTLAB_PROVISIONING_DB_POOL_MAX="${PLANTLAB_PROVISIONING_DB_POOL_MAX:-3}"
PLANTLAB_PROVISIONING_CLOUD_RUN_MAX_INSTANCES="${PLANTLAB_PROVISIONING_CLOUD_RUN_MAX_INSTANCES:-2}"
PLANTLAB_PROVISIONING_CLOUD_RUN_CONCURRENCY="${PLANTLAB_PROVISIONING_CLOUD_RUN_CONCURRENCY:-20}"

usage() {
  cat <<'USAGE'
Usage:
  platform/infra/cloud-run/deploy_provisioning_backend.sh <command>

Scope:
  Provisioning API only. This deploys the Express Cloud Run service used for
  setup-code, BLE claim-token, and hardware registration during onboarding.

Env loading:
  Reads platform/infra/env/.env. Values exported in the shell still work.
  platform/infra/env/.env.local is reserved for local dev and Docker flows.

Commands:
  print-config       Print non-secret deployment config.
  preflight          Check repo state, GCP resources, secrets, and service health.
  test-local         Run provisioning backend tests locally.
  build              Build and push an immutable image to Artifact Registry.
  deploy-candidate   Deploy a no-traffic candidate tagged "candidate".
  candidate-url      Print Cloud Run traffic/tag URLs.
  verify-health      Verify /health against VERIFY_URL.
  shift-traffic      Shift 100% traffic to candidate. Requires CONFIRM_SHIFT_TRAFFIC=yes.
  rollback           Roll back to ROLLBACK_REVISION.

Optional env:
  PLANTLAB_LOCAL_SETUP_URL, VERIFY_URL, IMAGE_URI,
  PLANTLAB_PROVISIONING_DEPLOY_STATE, PROVISIONING_SERVICE_NAME

Secrets are injected by Secret Manager name. Do not export secret values here.
USAGE
}

log() {
  printf '[provision-cloud-run] %s\n' "$*"
}

die() {
  printf '[provision-cloud-run] ERROR: %s\n' "$*" >&2
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

runtime_env_vars() {
  printf '%s' "^~^DB_NAME=${DB_NAME}~DB_USER=${DB_USER}~CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME}~PLANTLAB_LOCAL_SETUP_URL=${PLANTLAB_LOCAL_SETUP_URL}~PLANTLAB_PROVISIONING_DB_POOL_MAX=${PLANTLAB_PROVISIONING_DB_POOL_MAX}"
}

secret_bindings() {
  printf '%s' "DB_PASSWORD=db-password:latest,PLANTLAB_PROVISIONING_SHARED_SECRET=provisioning-shared-secret:latest"
}

cmd_print_config() {
  load_state
  cat <<EOF
PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
SERVICE_NAME=${SERVICE_NAME}
AR_REPO=${AR_REPO}
DB_INSTANCE=${DB_INSTANCE}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME}
RUN_SA=${RUN_SA}
PLANTLAB_LOCAL_SETUP_URL=${PLANTLAB_LOCAL_SETUP_URL}
PLANTLAB_PROVISIONING_DB_POOL_MAX=${PLANTLAB_PROVISIONING_DB_POOL_MAX}
PLANTLAB_PROVISIONING_CLOUD_RUN_MAX_INSTANCES=${PLANTLAB_PROVISIONING_CLOUD_RUN_MAX_INSTANCES}
PLANTLAB_PROVISIONING_CLOUD_RUN_CONCURRENCY=${PLANTLAB_PROVISIONING_CLOUD_RUN_CONCURRENCY}
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

  log "Confirming GCP resources"
  gcloud artifacts repositories describe "$AR_REPO" --location "$REGION"
  gcloud sql instances describe "$DB_INSTANCE"
  gcloud sql databases describe "$DB_NAME" --instance "$DB_INSTANCE"
  gcloud iam service-accounts describe "$RUN_SA"

  log "Confirming Secret Manager secrets exist"
  gcloud secrets describe db-password
  gcloud secrets describe provisioning-shared-secret

  log "Checking current provisioning service health"
  local current_url
  current_url="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)' 2>/dev/null || true)"
  if [ -n "$current_url" ]; then
    curl -fsS "${current_url}/health"
    printf '\n'
  else
    log "Service ${SERVICE_NAME} does not exist yet."
  fi
}

cmd_test_local() {
  require_command npm
  log "Running provisioning backend tests"
  (
    cd "$REPO_ROOT/provision_backend"
    npm test
  )
}

cmd_build() {
  require_command gcloud
  require_command git
  TAG="${TAG:-$(git -C "$REPO_ROOT" rev-parse --short HEAD)-provision-$(date -u +%Y%m%d%H%M%S)}"
  IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}:${TAG}"

  log "Building image: ${IMAGE_URI}"
  gcloud auth configure-docker "${REGION}-docker.pkg.dev"
  gcloud builds submit "$REPO_ROOT/provision_backend" --tag "$IMAGE_URI"
  save_state
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
    --set-cloudsql-instances "$CLOUD_SQL_CONNECTION_NAME" \
    --no-traffic \
    --tag candidate \
    --max-instances "$PLANTLAB_PROVISIONING_CLOUD_RUN_MAX_INSTANCES" \
    --concurrency "$PLANTLAB_PROVISIONING_CLOUD_RUN_CONCURRENCY" \
    --set-env-vars "$(runtime_env_vars)" \
    --set-secrets "$(secret_bindings)"
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
