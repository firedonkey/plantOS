#!/usr/bin/env bash

set -euo pipefail

MOBILE_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_APP_ROOT="$(cd "${MOBILE_SCRIPT_DIR}/../.." && pwd)"
DEFAULT_PROJECT_ROOT="$(cd "${MOBILE_APP_ROOT}/../.." && pwd)"

log() {
  printf '[mobile] %s\n' "$*"
}

warn() {
  printf '[mobile][WARN] %s\n' "$*" >&2
}

fail() {
  printf '[mobile][FAIL] %s\n' "$*" >&2
  exit 1
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

require_command() {
  local name="$1"
  local install_hint="$2"
  if ! has_command "$name"; then
    fail "Missing required command: ${name}. ${install_hint}"
  fi
}

abs_dir() {
  local dir="$1"
  (cd "$dir" && pwd -P)
}

package_uses_expo() {
  local package_json="$1"
  [[ -f "$package_json" ]] || return 1
  grep -Eq '"expo"[[:space:]]*:' "$package_json" || grep -Eq '"expo-router"[[:space:]]*:' "$package_json"
}

add_candidate_dir() {
  local candidate="$1"
  [[ -n "$candidate" && -d "$candidate" ]] || return 0
  local absolute
  absolute="$(abs_dir "$candidate")"
  if [[ " ${MOBILE_CANDIDATES:-} " != *" ${absolute} "* ]]; then
    MOBILE_CANDIDATES="${MOBILE_CANDIDATES:-} ${absolute}"
  fi
}

add_project_candidates() {
  local root="$1"
  [[ -n "$root" && -d "$root" ]] || return 0
  add_candidate_dir "$root"
  add_candidate_dir "$root/platform/mobile"
  add_candidate_dir "$root/mobile"
  add_candidate_dir "$root/app"
  add_candidate_dir "$root/apps/mobile"
  add_candidate_dir "$root/packages/mobile"
}

discover_mobile_dir() {
  if [[ -n "${MOBILE_APP_DIR:-}" ]]; then
    [[ -d "$MOBILE_APP_DIR" ]] || fail "MOBILE_APP_DIR does not exist: ${MOBILE_APP_DIR}"
    [[ -f "$MOBILE_APP_DIR/package.json" ]] || fail "MOBILE_APP_DIR has no package.json: ${MOBILE_APP_DIR}"
    package_uses_expo "$MOBILE_APP_DIR/package.json" || fail "MOBILE_APP_DIR does not look like an Expo app: ${MOBILE_APP_DIR}"
    abs_dir "$MOBILE_APP_DIR"
    return 0
  fi

  MOBILE_CANDIDATES=""
  add_candidate_dir "$PWD"
  add_candidate_dir "$MOBILE_APP_ROOT"
  add_project_candidates "${PLANTOS_PROJECT_ROOT:-}"
  add_project_candidates "$DEFAULT_PROJECT_ROOT"

  local candidate
  for candidate in ${MOBILE_CANDIDATES}; do
    if package_uses_expo "$candidate/package.json"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  local root
  for root in "$MOBILE_APP_ROOT" "${PLANTOS_PROJECT_ROOT:-}" "$DEFAULT_PROJECT_ROOT" "$PWD"; do
    [[ -n "$root" && -d "$root" ]] || continue
    if has_command python3; then
      while IFS= read -r package_json; do
        if package_uses_expo "$package_json"; then
          dirname "$package_json"
          return 0
        fi
      done < <(
        python3 - "$root" <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
skip = {"node_modules", ".git", "ios", "android", ".expo", "dist", "build"}
max_depth = 4
for current, dirs, files in os.walk(root):
    current_path = Path(current)
    depth = len(current_path.relative_to(root).parts)
    dirs[:] = [name for name in dirs if name not in skip and depth < max_depth]
    if "package.json" in files:
        print(current_path / "package.json")
PY
      )
    fi
  done

  fail "Could not find an Expo app. Run from the Expo app directory or set MOBILE_APP_DIR=/path/to/app."
}

cd_mobile_dir() {
  MOBILE_DIR="$(discover_mobile_dir)"
  cd "$MOBILE_DIR"
  log "Using Expo app: $MOBILE_DIR"
}

require_node_project() {
  [[ -f package.json ]] || fail "No package.json in $(pwd). Run from an Expo app or set MOBILE_APP_DIR."
  require_command node "Install Node.js."
  require_command npm "Install npm with Node.js."
}

require_node_modules() {
  [[ -d node_modules ]] || fail "node_modules is missing in $(pwd). Run npm install first."
}

package_has_script() {
  local script_name="$1"
  node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts[process.argv[1]] ? 0 : 1)" "$script_name"
}

package_has_dependency() {
  local dependency_name="$1"
  node -e "const p=require('./package.json'); const deps={...(p.dependencies||{}), ...(p.devDependencies||{})}; process.exit(deps[process.argv[1]] ? 0 : 1)" "$dependency_name"
}

run_package_script() {
  local script_name="$1"
  shift || true
  if [[ -f pnpm-lock.yaml ]] && has_command pnpm; then
    pnpm run "$script_name" "$@"
  elif [[ -f yarn.lock ]] && has_command yarn; then
    yarn "$script_name" "$@"
  else
    npm run "$script_name" -- "$@"
  fi
}

run_expo() {
  if [[ -x node_modules/.bin/expo ]]; then
    node_modules/.bin/expo "$@"
  else
    npx expo "$@"
  fi
}

require_expo_app() {
  require_node_project
  package_has_dependency expo || fail "package.json does not include expo. This script is for Expo/EAS projects."
}

run_eas() {
  if has_command eas; then
    eas "$@"
  else
    require_command npx "Install npm/npx or install eas-cli globally with npm install -g eas-cli."
    npx --yes eas-cli "$@"
  fi
}

require_eas_cli() {
  if has_command eas; then
    log "Using global eas CLI: $(command -v eas)"
    return 0
  fi
  if has_command npx; then
    log "Using eas-cli through npx."
    return 0
  fi
  fail "eas-cli is unavailable. Install it with npm install -g eas-cli, or install npm/npx."
}

require_eas_login() {
  if ! run_eas whoami >/dev/null 2>&1; then
    fail "EAS login required. Run: npx --yes eas-cli login"
  fi
  log "EAS login verified."
}

require_eas_json() {
  [[ -f eas.json ]] || fail "Missing eas.json in $(pwd). Add EAS build profiles before building."
}
