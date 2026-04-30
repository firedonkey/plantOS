#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIO_BIN="/Users/gary/plantOS/.venv/bin/pio"
PIO_CORE_DIR="/Users/gary/plantOS/.pio-core"

ENV_NAME="esp32-s3-devkitc-1"
PORT="/dev/cu.usbmodem1301"
OPEN_MONITOR=0

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [--test-dht22|--test-moisture|--test-actuators|--test-camera|--test-camera-platform|--test-wifi|--test-touch|--test-button-led|--test-espnow-master|--test-espnow-camera] [--port <serial_port>] [--monitor]

Options:
  --test-dht22      Flash dedicated DHT22 debug firmware (env: dht22-test)
  --test-moisture   Flash dedicated moisture debug firmware (env: moisture-test)
  --test-actuators  Flash dedicated light/pump debug firmware (env: actuators-test)
  --test-camera     Flash dedicated camera-node debug firmware (env: camera-test)
  --test-camera-platform  Flash camera-node platform uploader firmware (env: camera-platform-test)
  --test-wifi       Flash dedicated XIAO Wi-Fi test firmware (env: wifi-test)
  --test-touch      Flash dedicated touch-button debug firmware (env: touch-test)
  --test-button-led Flash dedicated physical-button + status-led test firmware (env: button-led-test)
  --test-espnow-master  Flash dedicated ESP-NOW master link-test firmware (env: espnow-master-test)
  --test-espnow-camera  Flash dedicated ESP-NOW camera link-test firmware (env: espnow-camera-test)
  --port <port>     Serial port (default: ${PORT})
  --monitor         Open serial monitor after upload
  --help            Show this message

Examples:
  $(basename "$0")
  $(basename "$0") --monitor
  $(basename "$0") --test-dht22 --monitor
  $(basename "$0") --test-moisture --monitor
  $(basename "$0") --test-actuators --monitor
  $(basename "$0") --test-camera --port /dev/cu.usbmodem12201 --monitor
  $(basename "$0") --test-camera-platform --port /dev/cu.usbmodem12201 --monitor
  $(basename "$0") --test-wifi --port /dev/cu.usbmodem12201 --monitor
  $(basename "$0") --test-touch --monitor
  $(basename "$0") --test-button-led --monitor
  $(basename "$0") --test-espnow-master --port /dev/cu.usbmodem1301 --monitor
  $(basename "$0") --test-espnow-camera --port /dev/cu.usbmodem12201 --monitor
  $(basename "$0") --port /dev/cu.usbmodem1301 --monitor
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
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
    --port)
      PORT="${2:-}"
      if [[ -z "${PORT}" ]]; then
        echo "Error: --port requires a value."
        exit 1
      fi
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
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ ! -x "${PIO_BIN}" ]]; then
  echo "Error: pio not found at ${PIO_BIN}"
  echo "Install it first in /Users/gary/plantOS/.venv"
  exit 1
fi

echo "[plantlab] env: ${ENV_NAME}"
echo "[plantlab] port: ${PORT}"
echo "[plantlab] project: ${PROJECT_DIR}"

export PLATFORMIO_CORE_DIR="${PIO_CORE_DIR}"

cd "${PROJECT_DIR}"

echo "[plantlab] building firmware..."
"${PIO_BIN}" run -e "${ENV_NAME}"

echo "[plantlab] uploading firmware..."
"${PIO_BIN}" run -e "${ENV_NAME}" -t upload --upload-port "${PORT}"

if [[ "${OPEN_MONITOR}" -eq 1 ]]; then
  echo "[plantlab] opening serial monitor..."
  "${PIO_BIN}" device monitor --port "${PORT}" -b 115200
fi
