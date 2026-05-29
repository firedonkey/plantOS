#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LOCAL_ENV_ARGS=()
EXPO_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-url|--wifi-ssid-options)
      [[ $# -ge 2 ]] || {
        printf '[mobile][FAIL] %s requires a value.\n' "$1" >&2
        exit 1
      }
      LOCAL_ENV_ARGS+=("$1" "$2")
      shift 2
      ;;
    --skip-backend-check)
      LOCAL_ENV_ARGS+=("$1")
      shift
      ;;
    *)
      EXPO_ARGS+=("$1")
      shift
      ;;
  esac
done

"${SCRIPT_DIR}/write_local_env.sh" "${LOCAL_ENV_ARGS[@]}"
"${SCRIPT_DIR}/start_dev_client.sh" "${EXPO_ARGS[@]}"
