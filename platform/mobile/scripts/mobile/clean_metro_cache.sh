#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_common.sh
source "${SCRIPT_DIR}/_common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/mobile/clean_metro_cache.sh

Clears common Metro, haste-map, and Watchman state for an Expo/React Native app.

Environment:
  MOBILE_APP_DIR=/path/to/expo-app   Optional explicit Expo app directory.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

cd_mobile_dir
require_command python3 "Install Python 3 or clear Metro cache manually."

log "Clearing Watchman watches if Watchman is installed."
if has_command watchman; then
  if watchman watch-del-all >/dev/null 2>&1; then
    log "Watchman watches cleared."
  else
    warn "watchman watch-del-all failed; continuing with Metro cache cleanup."
  fi
else
  warn "Watchman is not installed. Skipping watchman cleanup."
fi

log "Clearing Metro and haste-map cache files from safe temp/cache locations."
python3 - <<'PY'
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

patterns = (
    "metro-*",
    "metro-cache",
    "haste-map-*",
    "react-native-packager-cache-*",
)

roots: list[Path] = []
for raw in {os.environ.get("TMPDIR"), tempfile.gettempdir(), "/tmp"}:
    if raw:
        root = Path(raw).expanduser()
        if root.exists() and root not in roots:
            roots.append(root)

removed: list[Path] = []
for root in roots:
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.exists():
                continue
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed.append(path)
            except FileNotFoundError:
                continue
            except OSError as exc:
                print(f"[mobile][WARN] could not remove {path}: {exc}")

print(f"[mobile] Removed {len(removed)} cache path(s).")
for path in removed[:20]:
    print(f"[mobile] removed {path}")
if len(removed) > 20:
    print(f"[mobile] ...and {len(removed) - 20} more")
PY

if [[ -d node_modules/.cache/metro ]]; then
  rm -rf node_modules/.cache/metro
  log "Removed node_modules/.cache/metro."
fi

log "Metro cache cleanup complete."
