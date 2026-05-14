#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/mobile/register_ios_device.sh [eas device:create args...]

Registers an iPhone/iPad with EAS for internal iOS development builds.

Examples:
  scripts/mobile/register_ios_device.sh
  scripts/mobile/register_ios_device.sh --apple-team-id TEAMID

Environment:
  MOBILE_APP_DIR=/path/to/expo-app   Optional explicit Expo app directory.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

cd_mobile_dir
require_expo_app
require_eas_cli
require_eas_login

cat <<'EOF'
[mobile] iOS device registration flow:
[mobile] 1. Keep the target iPhone nearby.
[mobile] 2. EAS will provide a registration link or QR code.
[mobile] 3. Open it on the iPhone and install the registration profile.
[mobile] 4. Return to this terminal and let EAS finish device registration.
[mobile] No Apple secrets are printed by this script.
EOF

run_eas device:create "$@"
