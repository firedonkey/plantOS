#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

ENV_NAME="esp32-s3-devkitc-1"
PORT="${PLANTLAB_SERIAL_PORT:-}"
PORT_WAS_PROVIDED=0
OPEN_MONITOR=0
MODE="dry-run"

if [[ -n "${PORT}" ]]; then
  PORT_WAS_PROVIDED=1
fi

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

log() {
  printf '[plantlab] %s\n' "$*"
}

quote_cmd() {
  local quoted=()
  local part
  for part in "$@"; do
    printf -v part '%q' "$part"
    quoted+=("$part")
  done
  printf '%s\n' "${quoted[*]}"
}

resolve_pio_bin() {
  if [[ -n "${PIO_BIN:-}" ]]; then
    if [[ -x "${PIO_BIN}" ]]; then
      return
    fi
    if command -v "${PIO_BIN}" >/dev/null 2>&1; then
      PIO_BIN="$(command -v "${PIO_BIN}")"
      return
    fi
    fail "PIO_BIN is set to '${PIO_BIN}', but it is not executable. Install PlatformIO or update PIO_BIN."
  fi

  if [[ -x "${REPO_ROOT}/.venv/bin/pio" ]]; then
    PIO_BIN="${REPO_ROOT}/.venv/bin/pio"
    return
  fi

  if command -v pio >/dev/null 2>&1; then
    PIO_BIN="$(command -v pio)"
    return
  fi

  fail "PlatformIO CLI not found. Run scripts/setup_new_machine.sh --python or install pio and set PIO_BIN."
}

validate_project() {
  if [[ ! -f "${PROJECT_DIR}/platformio.ini" ]]; then
    fail "PlatformIO project file missing: ${PROJECT_DIR}/platformio.ini"
  fi
}

detect_serial_ports() {
  local pattern
  local candidate
  for pattern in /dev/cu.usbmodem* /dev/cu.usbserial* /dev/ttyACM* /dev/ttyUSB*; do
    for candidate in ${pattern}; do
      if [[ -e "${candidate}" ]]; then
        printf '%s\n' "${candidate}"
      fi
    done
  done | sort -u
}

select_serial_port() {
  local candidates=()
  local candidate
  while IFS= read -r candidate; do
    if [[ -n "${candidate}" ]]; then
      candidates+=("${candidate}")
    fi
  done < <(detect_serial_ports)

  if [[ "${PORT_WAS_PROVIDED}" -eq 1 ]]; then
    return
  fi

  if [[ "${#candidates[@]}" -eq 1 ]]; then
    PORT="${candidates[0]}"
    return
  fi

  if [[ "${MODE}" == "flash" ]]; then
    if [[ "${#candidates[@]}" -eq 0 ]]; then
      fail "No serial port detected. Connect the ESP32 or pass --port /dev/<device>."
    fi

    printf 'Detected multiple candidate serial ports:\n' >&2
    printf '  %s\n' "${candidates[@]}" >&2
    fail "Pass --port explicitly before flashing."
  fi
}

release_port_if_busy() {
  if [[ -z "${PORT}" ]]; then
    return
  fi
  if ! command -v lsof >/dev/null 2>&1; then
    return
  fi

  local pids
  pids="$(lsof -t "${PORT}" 2>/dev/null || true)"
  pids="$(printf '%s' "${pids}" | tr '\n' ' ')"
  if [[ -z "${pids// }" ]]; then
    return
  fi

  log "releasing serial port ${PORT} from existing process(es): ${pids}"
  local pid
  for pid in ${pids}; do
    if [[ "${pid}" != "$$" ]]; then
      kill "${pid}" 2>/dev/null || true
    fi
  done

  sleep 1
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [environment] [mode] [--port <serial_port>] [--monitor]

Environment:
  --local                Main firmware with explicit local provisioning profile (env: esp32-local)
  --gcp                  Main firmware with explicit GCP provisioning profile (env: esp32-gcp)
  --test-dht22           Dedicated DHT22 debug firmware (env: dht22-test)
  --test-moisture        Dedicated moisture debug firmware (env: moisture-test)
  --test-actuators       Dedicated light/pump debug firmware (env: actuators-test)
  --test-camera          Dedicated camera-node debug firmware (env: camera-test)
  --test-camera-platform Camera-node platform uploader firmware (env: camera-platform-test)
  --test-wifi            Dedicated XIAO Wi-Fi test firmware (env: wifi-test)
  --test-touch           Dedicated touch-button debug firmware (env: touch-test)
  --test-button-led      Dedicated physical-button + status-led test firmware (env: button-led-test)
  --test-espnow-master   Dedicated ESP-NOW master link-test firmware (env: espnow-master-test)
  --test-espnow-camera   Dedicated ESP-NOW camera link-test firmware (env: espnow-camera-test)

Mode:
  --dry-run, --check     Print resolved commands only. This is the default.
  --build-only           Build selected firmware; do not upload to hardware.
  --flash                Build and upload selected firmware. Required for any flash operation.

Options:
  --port <port>          Serial port. If omitted, one detected port is selected; multiple ports require --port.
  --monitor              Open serial monitor after --flash upload.
  --help                 Show this message.

Examples:
  $(basename "$0") --test-camera-platform --dry-run
  $(basename "$0") --test-camera-platform --build-only
  $(basename "$0") --test-camera-platform --port /dev/cu.usbmodem12201 --flash --monitor
  $(basename "$0") --local --port /dev/cu.usbmodem11401 --flash
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)
      ENV_NAME="esp32-local"
      shift
      ;;
    --gcp)
      ENV_NAME="esp32-gcp"
      shift
      ;;
    --test-dht22)
      ENV_NAME="dht22-test"
      shift
      ;;
    --test-moisture)
      ENV_NAME="moisture-test"
      shift
      ;;
    --test-actuators)
      ENV_NAME="actuators-test"
      shift
      ;;
    --test-camera)
      ENV_NAME="camera-test"
      shift
      ;;
    --test-camera-platform)
      ENV_NAME="camera-platform-test"
      shift
      ;;
    --test-wifi)
      ENV_NAME="wifi-test"
      shift
      ;;
    --test-touch)
      ENV_NAME="touch-test"
      shift
      ;;
    --test-button-led)
      ENV_NAME="button-led-test"
      shift
      ;;
    --test-espnow-master)
      ENV_NAME="espnow-master-test"
      shift
      ;;
    --test-espnow-camera)
      ENV_NAME="espnow-camera-test"
      shift
      ;;
    --dry-run|--check)
      MODE="dry-run"
      shift
      ;;
    --build-only)
      MODE="build-only"
      shift
      ;;
    --flash)
      MODE="flash"
      shift
      ;;
    --port)
      PORT="${2:-}"
      if [[ -z "${PORT}" ]]; then
        fail "--port requires a value."
      fi
      PORT_WAS_PROVIDED=1
      shift 2
      ;;
    --monitor)
      OPEN_MONITOR=1
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

resolve_pio_bin
validate_project
: "${PLATFORMIO_CORE_DIR:=${REPO_ROOT}/.pio-core}"
export PLATFORMIO_CORE_DIR
select_serial_port

build_cmd=("${PIO_BIN}" run -d "${PROJECT_DIR}" -e "${ENV_NAME}")
upload_cmd=("${PIO_BIN}" run -d "${PROJECT_DIR}" -e "${ENV_NAME}" -t upload)
monitor_cmd=("${PIO_BIN}" device monitor -b 115200)

if [[ -n "${PORT}" ]]; then
  upload_cmd+=(--upload-port "${PORT}")
  monitor_cmd+=(--port "${PORT}")
fi

log "repo root: ${REPO_ROOT}"
log "project: ${PROJECT_DIR}"
log "env: ${ENV_NAME}"
log "mode: ${MODE}"
log "pio: ${PIO_BIN}"
log "PlatformIO core: ${PLATFORMIO_CORE_DIR}"
if [[ -n "${PORT}" ]]; then
  log "serial port: ${PORT}"
else
  log "serial port: not selected; pass --port before flashing if multiple devices are attached"
fi
log "build command: $(quote_cmd "${build_cmd[@]}")"
if [[ -n "${PORT}" ]]; then
  log "flash command: $(quote_cmd "${upload_cmd[@]}")"
else
  log "flash command: requires --port when more than one candidate serial device exists"
fi
if [[ "${OPEN_MONITOR}" -eq 1 ]]; then
  if [[ -n "${PORT}" ]]; then
    log "monitor command: $(quote_cmd "${monitor_cmd[@]}")"
  else
    log "monitor command: requires --port"
  fi
fi

case "${MODE}" in
  dry-run)
    log "dry run complete; no build, upload, or monitor command was run"
    ;;
  build-only)
    log "building firmware only"
    "${build_cmd[@]}"
    ;;
  flash)
    if [[ -z "${PORT}" ]]; then
      fail "A serial port is required for --flash. Pass --port /dev/<device>."
    fi
    log "building firmware"
    "${build_cmd[@]}"
    release_port_if_busy
    log "uploading firmware"
    "${upload_cmd[@]}"
    if [[ "${OPEN_MONITOR}" -eq 1 ]]; then
      log "opening serial monitor"
      "${monitor_cmd[@]}"
    fi
    ;;
  *)
    fail "Unknown mode: ${MODE}"
    ;;
esac
