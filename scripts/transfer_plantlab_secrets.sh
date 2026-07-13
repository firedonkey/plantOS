#!/usr/bin/env bash
set -euo pipefail

SRC="/Users/gary/plantOS"
DEST="/Users/gary/plantOS"
REMOTE_USER="gary"
REMOTE_HOST="192.168.0.45"
USE_CONTROL_MASTER=1

usage() {
  cat <<'EOF'
Usage:
  scripts/transfer_plantlab_secrets.sh [options]

Options:
  --source <path>       Source PlantLab repo. Default: /Users/gary/plantOS
  --dest <path>         Destination PlantLab repo. Default: /Users/gary/plantOS
  --user <user>         SSH user. Default: gary
  --host <host>         SSH host. Default: 192.168.0.45
  --no-control-master   Do not use SSH connection sharing.
  --help                Show this message.

Copies only approved PlantLab secret files. It never prints secret contents or
checksums. SSH host-key checking remains enabled.
EOF
}

log() {
  printf '[plantlab-secret-transfer] %s\n' "$*"
}

fail() {
  printf '[plantlab-secret-transfer][ERROR] %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SRC="${2:-}"
      [[ -n "$SRC" ]] || fail "--source requires a value"
      shift 2
      ;;
    --dest)
      DEST="${2:-}"
      [[ -n "$DEST" ]] || fail "--dest requires a value"
      shift 2
      ;;
    --user)
      REMOTE_USER="${2:-}"
      [[ -n "$REMOTE_USER" ]] || fail "--user requires a value"
      shift 2
      ;;
    --host)
      REMOTE_HOST="${2:-}"
      [[ -n "$REMOTE_HOST" ]] || fail "--host requires a value"
      shift 2
      ;;
    --no-control-master)
      USE_CONTROL_MASTER=0
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

[[ -d "$SRC" ]] || fail "Source repository does not exist: $SRC"

REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP="/Users/gary/.plantlab_migration_backup/${TS}"
MANIFEST="$(mktemp)"
SKIPPED="$(mktemp)"
BACKUPS="$(mktemp)"
CONTROL_PATH="/tmp/plantlab-secret-transfer-${REMOTE_USER}@${REMOTE_HOST}:22"
CONTROL_STARTED=0

SSH_OPTS=(-o StrictHostKeyChecking=yes)
SCP_OPTS=(-o StrictHostKeyChecking=yes)

cleanup() {
  rm -f "$MANIFEST" "$SKIPPED" "$BACKUPS"
  if [[ "$CONTROL_STARTED" -eq 1 ]]; then
    ssh -o ControlPath="$CONTROL_PATH" -O exit "$REMOTE" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ "$USE_CONTROL_MASTER" -eq 1 ]]; then
  SSH_OPTS+=(-o ControlMaster=auto -o ControlPath="$CONTROL_PATH" -o ControlPersist=10m)
  SCP_OPTS+=(-o ControlMaster=auto -o ControlPath="$CONTROL_PATH" -o ControlPersist=10m)
fi

log "remote: ${REMOTE}"
log "source repo: ${SRC}"
log "destination repo: ${DEST}"
log "backup root on new Mac: ${BACKUP}"

if [[ "$USE_CONTROL_MASTER" -eq 1 ]]; then
  log "opening SSH control connection; enter password if prompted"
  ssh "${SSH_OPTS[@]}" -MNf "$REMOTE"
  CONTROL_STARTED=1
fi

log "checking SSH connectivity"
ssh "${SSH_OPTS[@]}" "$REMOTE" 'printf "SSH_OK\n"'

log "checking destination repository"
ssh "${SSH_OPTS[@]}" "$REMOTE" "test -d '$DEST' && printf 'DEST_REPO_EXISTS\n'"

approved_dirs=(
  "$SRC"
  "$SRC/platform/infra/env"
  "$SRC/platform/web"
  "$SRC/platform/mobile"
  "$SRC/provision_backend"
)

for dir in "${approved_dirs[@]}"; do
  rel_dir="${dir#$SRC}"
  rel_dir="${rel_dir#/}"
  if [[ ! -d "$dir" ]]; then
    printf 'missing source directory: %s\n' "${rel_dir:-.}" >> "$SKIPPED"
    continue
  fi

  before_count="$(wc -l < "$MANIFEST" | tr -d ' ')"
  find "$dir" -maxdepth 1 -type f \( -name ".env" -o -name ".env.*" \) \
    ! -iname "*example*" \
    ! -iname "*sample*" \
    ! -iname "*template*" \
    -print | sed "s#^$SRC/##" >> "$MANIFEST"
  after_count="$(wc -l < "$MANIFEST" | tr -d ' ')"

  if [[ "$after_count" == "$before_count" ]]; then
    printf 'no approved env files in: %s\n' "${rel_dir:-.}" >> "$SKIPPED"
  fi
done

if [[ -f "$SRC/device/esp32/include/platform_secrets.h" ]]; then
  printf '%s\n' "device/esp32/include/platform_secrets.h" >> "$MANIFEST"
else
  printf '%s\n' "missing file: device/esp32/include/platform_secrets.h" >> "$SKIPPED"
fi

sort -u "$MANIFEST" -o "$MANIFEST"

printf 'Filename-only manifest:\n'
if [[ -s "$MANIFEST" ]]; then
  sed 's#^#  #' "$MANIFEST"
else
  printf '  <none>\n'
fi

printf 'Skipped source locations/files:\n'
if [[ -s "$SKIPPED" ]]; then
  sort -u "$SKIPPED" | sed 's#^#  #'
else
  printf '  <none>\n'
fi

if [[ ! -s "$MANIFEST" ]]; then
  log "no approved files found; nothing to copy"
  exit 0
fi

checksum_failures=0
copied_count=0

while IFS= read -r rel; do
  [[ -n "$rel" ]] || continue

  remote_file="${DEST}/${rel}"
  remote_dir="$(dirname "$remote_file")"
  backup_file="${BACKUP}/${rel}"
  backup_dir="$(dirname "$backup_file")"

  backup_output="$(ssh -n "${SSH_OPTS[@]}" "$REMOTE" "
    set -e
    mkdir -p '$remote_dir' '$backup_dir'
    if [ -f '$remote_file' ]; then
      cp -p '$remote_file' '$backup_file'
      printf 'BACKUP %s\n' '$rel'
    else
      printf 'NO_BACKUP_NEEDED %s\n' '$rel'
    fi
  ")"
  printf '%s\n' "$backup_output" | tee -a "$BACKUPS"

  scp -p "${SCP_OPTS[@]}" "$SRC/$rel" "$REMOTE:$remote_file" >/dev/null
  ssh -n "${SSH_OPTS[@]}" "$REMOTE" "chmod 600 '$remote_file'"

  src_sum="$(shasum -a 256 "$SRC/$rel" | cut -d ' ' -f 1)"
  dst_sum="$(ssh -n "${SSH_OPTS[@]}" "$REMOTE" "shasum -a 256 '$remote_file' | cut -d ' ' -f 1")"

  if [[ "$src_sum" == "$dst_sum" ]]; then
    printf 'CHECKSUM PASS %s\n' "$rel"
  else
    printf 'CHECKSUM FAIL %s\n' "$rel"
    checksum_failures=$((checksum_failures + 1))
  fi
  copied_count=$((copied_count + 1))
done < "$MANIFEST"

printf 'Remote git status:\n'
ssh "${SSH_OPTS[@]}" "$REMOTE" "cd '$DEST' && git status --short"

printf 'Git-ignore verification:\n'
ignore_failures=0
while IFS= read -r rel; do
  [[ -n "$rel" ]] || continue
  if ssh -n "${SSH_OPTS[@]}" "$REMOTE" "cd '$DEST' && git check-ignore -q '$rel'"; then
    printf 'IGNORED PASS %s\n' "$rel"
  else
    printf 'IGNORED FAIL %s\n' "$rel"
    ignore_failures=$((ignore_failures + 1))
  fi
done < "$MANIFEST"

printf 'Transfer summary:\n'
printf '  copied file count: %s\n' "$copied_count"
printf '  backup root: %s\n' "$BACKUP"
printf '  checksum failures: %s\n' "$checksum_failures"
printf '  git-ignore failures: %s\n' "$ignore_failures"

if [[ "$checksum_failures" -ne 0 || "$ignore_failures" -ne 0 ]]; then
  exit 1
fi
