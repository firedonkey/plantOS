#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DO_PYTHON=0
DO_NODE=0
DO_ENV=0

usage() {
  cat <<'EOF'
Usage:
  scripts/setup_new_machine.sh [--check|--python|--node|--env|--all]

Options:
  --check   Check required tools only. This is the default.
  --python  Create/update .venv and install backend + PlatformIO dependencies.
  --node    Install Node dependencies for web, mobile, and provisioning backend.
  --env     Create local env files from examples when missing.
  --all     Run --python, --node, and --env.

This script does not install system tools such as Git, Docker, gcloud, Xcode,
or Node. It does not write real secrets.
EOF
}

log() {
  printf '[setup] %s\n' "$*"
}

warn() {
  printf '[setup][WARN] %s\n' "$*" >&2
}

fail() {
  printf '[setup][ERROR] %s\n' "$*" >&2
  exit 1
}

install_hint() {
  case "$1" in
    git) printf 'Install Git and configure GitHub SSH access.' ;;
    python3) printf 'Install Python 3 with venv support.' ;;
    node|npm) printf 'Install Node.js and npm.' ;;
    docker) printf 'Install Docker Desktop or Docker Engine.' ;;
    gcloud) printf 'Install Google Cloud CLI for deployment workflows.' ;;
    *) printf 'Install the missing command and retry.' ;;
  esac
}

command_version() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    return 1
  fi

  case "$name" in
    gcloud)
      "$name" --version | head -1
      ;;
    docker|git|python3|node|npm)
      "$name" --version | head -1
      ;;
    *)
      command -v "$name"
      ;;
  esac
}

node_required_major() {
  local version_file=""
  if [[ -f "${ROOT_DIR}/.nvmrc" ]]; then
    version_file="${ROOT_DIR}/.nvmrc"
  elif [[ -f "${ROOT_DIR}/.node-version" ]]; then
    version_file="${ROOT_DIR}/.node-version"
  else
    return 1
  fi

  local value
  value="$(tr -d '[:space:]' < "${version_file}")"
  value="${value#v}"
  value="${value%%.*}"
  if [[ -z "${value}" || ! "${value}" =~ ^[0-9]+$ ]]; then
    warn "unable to parse Node version pin from ${version_file}"
    return 1
  fi
  printf '%s\n' "${value}"
}

node_active_major() {
  local value
  value="$(node --version 2>/dev/null || true)"
  value="${value#v}"
  value="${value%%.*}"
  if [[ -z "${value}" || ! "${value}" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  printf '%s\n' "${value}"
}

check_node_version_pin() {
  if ! command -v node >/dev/null 2>&1; then
    return 1
  fi

  local required
  if ! required="$(node_required_major)"; then
    warn "no .nvmrc or .node-version Node pin found"
    return 0
  fi

  local active
  if ! active="$(node_active_major)"; then
    warn "unable to parse active Node version"
    return 1
  fi

  if [[ "${active}" == "${required}" ]]; then
    log "node pin: active major ${active} matches required ${required}"
    return 0
  fi

  warn "node pin mismatch: active major ${active}, required ${required}. Run nvm use or install Node ${required}."
  return 1
}

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    fail "Missing command: ${name}. $(install_hint "$name")"
  fi
}

report_tooling() {
  log "repo: ${ROOT_DIR}"
  log "os: $(uname -s) $(uname -m)"
  if command -v sw_vers >/dev/null 2>&1; then
    log "macOS: $(sw_vers -productVersion)"
  fi

  local name
  local missing=0
  for name in git python3 node npm docker; do
    if command_version "$name" >/dev/null 2>&1; then
      log "${name}: $(command_version "$name")"
    else
      warn "missing ${name}: $(install_hint "$name")"
      missing=1
    fi
  done

  check_node_version_pin || missing=1

  if command_version gcloud >/dev/null 2>&1; then
    log "gcloud: $(command_version gcloud)"
  else
    warn "missing gcloud: $(install_hint gcloud)"
  fi

  return "$missing"
}

print_plan() {
  if [[ "$DO_PYTHON$DO_NODE$DO_ENV" == "000" ]]; then
    log "plan: check tools only; no files will be generated or modified"
    return
  fi

  log "plan:"
  if [[ "$DO_PYTHON" -eq 1 ]]; then
    log "  - create/update .venv and install backend requirements plus PlatformIO"
  fi
  if [[ "$DO_NODE" -eq 1 ]]; then
    log "  - run npm ci in platform/web and platform/mobile"
    log "  - run npm install in provision_backend because no package-lock.json is currently committed"
  fi
  if [[ "$DO_ENV" -eq 1 ]]; then
    log "  - copy example env/secret-template files only when local files are missing"
    log "  - generated files contain placeholders; edit them locally and do not commit real secrets"
  fi
}

copy_if_missing() {
  local src="$1"
  local dest="$2"
  if [[ -e "$dest" ]]; then
    log "exists: ${dest}"
    return
  fi
  if [[ ! -f "$src" ]]; then
    warn "missing template: ${src}"
    return
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  log "created ${dest} from ${src}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      shift
      ;;
    --python)
      DO_PYTHON=1
      shift
      ;;
    --node)
      DO_NODE=1
      shift
      ;;
    --env)
      DO_ENV=1
      shift
      ;;
    --all)
      DO_PYTHON=1
      DO_NODE=1
      DO_ENV=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage
      exit 1
      ;;
  esac
done

cd "$ROOT_DIR"

print_plan
if ! report_tooling; then
  if [[ "$DO_PYTHON$DO_NODE$DO_ENV" == "000" ]]; then
    fail "One or more required development tools are missing."
  fi
fi

if [[ "$DO_PYTHON" -eq 1 ]]; then
  require_command python3
  log "creating/updating Python virtualenv"
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r platform/backend/requirements.txt
  .venv/bin/python -m pip install platformio
fi

if [[ "$DO_NODE" -eq 1 ]]; then
  require_command node
  require_command npm
  log "installing Node dependencies"
  npm --prefix platform/web ci
  npm --prefix platform/mobile ci
  npm --prefix provision_backend install
fi

if [[ "$DO_ENV" -eq 1 ]]; then
  log "creating local env files from examples when missing"
  copy_if_missing .env.example .env
  copy_if_missing .env.local.example platform/infra/env/.env.local
  copy_if_missing platform/web/.env.example platform/web/.env
  copy_if_missing platform/mobile/.env.example platform/mobile/.env
  copy_if_missing provision_backend/.env.example provision_backend/.env
  copy_if_missing device/esp32/include/platform_secrets.example.h device/esp32/include/platform_secrets.h
fi

log "done"
