#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RUN_DOCS=0
RUN_BACKEND=0
RUN_WEB=0
RUN_MOBILE=0
RUN_PROVISION=0
RUN_SIMULATOR=0
RUN_FIRMWARE=0

usage() {
  cat <<'EOF'
Usage:
  scripts/validate_repo.sh [--docs] [--backend] [--web] [--mobile] [--provision] [--simulator] [--firmware] [--all]

Options:
  --docs        Run git diff whitespace check and shell syntax checks.
  --backend     Run backend pytest suite.
  --web         Run web unit tests, typecheck, and build.
  --mobile      Run mobile typecheck and unit tests.
  --provision   Run provisioning backend tests.
  --simulator   Run simulator smoke tests and compile check.
  --firmware    Build key ESP32 PlatformIO environments; does not upload to hardware.
  --all         Run every group.

When no options are provided, --docs is used. No option flashes hardware,
deploys to cloud infrastructure, or modifies production data.
EOF
}

log() {
  printf '[validate] %s\n' "$*"
}

fail() {
  printf '[validate][ERROR] %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  local name="$1"
  local hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    fail "Missing command: ${name}. ${hint}"
  fi
}

need_file() {
  local path="$1"
  local hint="$2"
  if [[ ! -e "$path" ]]; then
    fail "Missing ${path}. ${hint}"
  fi
}

run_cmd() {
  log "$*"
  "$@"
}

print_plan() {
  log "repo: ${ROOT_DIR}"
  log "plan:"
  if [[ "$RUN_DOCS" -eq 1 ]]; then
    log "  - docs/static: git diff --check and shell syntax"
  fi
  if [[ "$RUN_BACKEND" -eq 1 ]]; then
    log "  - backend: pytest platform/backend/tests"
  fi
  if [[ "$RUN_WEB" -eq 1 ]]; then
    log "  - web: node tests, typecheck, build"
  fi
  if [[ "$RUN_MOBILE" -eq 1 ]]; then
    log "  - mobile: typecheck and unit tests"
  fi
  if [[ "$RUN_PROVISION" -eq 1 ]]; then
    log "  - provisioning backend: npm test"
  fi
  if [[ "$RUN_SIMULATOR" -eq 1 ]]; then
    log "  - simulator: smoke tests and compile check"
  fi
  if [[ "$RUN_FIRMWARE" -eq 1 ]]; then
    log "  - firmware: PlatformIO build only, no upload"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docs)
      RUN_DOCS=1
      shift
      ;;
    --backend)
      RUN_BACKEND=1
      shift
      ;;
    --web)
      RUN_WEB=1
      shift
      ;;
    --mobile)
      RUN_MOBILE=1
      shift
      ;;
    --provision)
      RUN_PROVISION=1
      shift
      ;;
    --simulator)
      RUN_SIMULATOR=1
      shift
      ;;
    --firmware)
      RUN_FIRMWARE=1
      shift
      ;;
    --all)
      RUN_DOCS=1
      RUN_BACKEND=1
      RUN_WEB=1
      RUN_MOBILE=1
      RUN_PROVISION=1
      RUN_SIMULATOR=1
      RUN_FIRMWARE=1
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

if [[ "$RUN_DOCS$RUN_BACKEND$RUN_WEB$RUN_MOBILE$RUN_PROVISION$RUN_SIMULATOR$RUN_FIRMWARE" == "0000000" ]]; then
  RUN_DOCS=1
fi

cd "$ROOT_DIR"
print_plan

if [[ "$RUN_DOCS" -eq 1 ]]; then
  need_cmd git "Install Git before validating repository diffs."
  need_cmd bash "Install Bash before validating shell syntax."
  run_cmd git diff --check
  run_cmd bash -n scripts/setup_new_machine.sh scripts/validate_repo.sh device/esp32/scripts/flash_esp32.sh
fi

if [[ "$RUN_BACKEND" -eq 1 ]]; then
  need_file .venv/bin/pytest "Run scripts/setup_new_machine.sh --python first."
  run_cmd .venv/bin/pytest platform/backend/tests -q
fi

if [[ "$RUN_WEB" -eq 1 ]]; then
  need_cmd node "Install Node.js and run scripts/setup_new_machine.sh --node first."
  need_cmd npm "Install npm and run scripts/setup_new_machine.sh --node first."
  run_cmd node --test platform/web/test/*.test.js
  run_cmd npm --prefix platform/web run typecheck
  run_cmd npm --prefix platform/web run build
fi

if [[ "$RUN_MOBILE" -eq 1 ]]; then
  need_cmd npm "Install npm and run scripts/setup_new_machine.sh --node first."
  run_cmd npm --prefix platform/mobile run typecheck
  run_cmd npm --prefix platform/mobile run test:unit
fi

if [[ "$RUN_PROVISION" -eq 1 ]]; then
  need_cmd npm "Install npm and run scripts/setup_new_machine.sh --node first."
  run_cmd npm --prefix provision_backend test
fi

if [[ "$RUN_SIMULATOR" -eq 1 ]]; then
  need_cmd python3 "Install Python 3 before simulator validation."
  need_file .venv/bin/pytest "Run scripts/setup_new_machine.sh --python first."
  run_cmd .venv/bin/pytest tools/simulator/test_simulator_smoke.py -q
  run_cmd python3 -m compileall -q tools/simulator
fi

if [[ "$RUN_FIRMWARE" -eq 1 ]]; then
  need_file .venv/bin/pio "Run scripts/setup_new_machine.sh --python first."
  run_cmd .venv/bin/pio run -d device/esp32 -e esp32-local
  run_cmd .venv/bin/pio run -d device/esp32 -e camera-platform-test
fi

log "done"
