# Test Log

This file records validation commands relevant to migration prep. It is not a replacement for CI.

## 2026-06-26 Migration Prep

Repository inspection commands run:

```bash
git status --short
git branch --show-current
git rev-parse --short HEAD
git rev-parse --short origin/main
git remote -v
find . -maxdepth 3 -type f
find scripts device/esp32/scripts platform/infra/scripts platform/infra/cloud-run -maxdepth 2 -type f
git ls-files | xargs -I{} du -k {} | sort -nr | head -40
```

Results:

- Local branch before migration-prep docs: `main`.
- Local and remote commits before migration-prep docs: `1e0757d`.
- Only untracked root `data/` runtime artifacts were present before migration-prep docs.
- No Git LFS tracked files were found.

Initial migration-prep validation commands:

```bash
scripts/validate_repo.sh --docs
scripts/setup_new_machine.sh --check
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --dry-run
/Users/gary/plantOS/scripts/validate_repo.sh --docs
/Users/gary/plantOS/scripts/setup_new_machine.sh --check
/Users/gary/plantOS/device/esp32/scripts/flash_esp32.sh --test-camera-platform --dry-run
```

Results:

- `scripts/validate_repo.sh --docs`: PASS.
- `scripts/setup_new_machine.sh --check`: PASS. It reported Google Cloud SDK `565.0.0` and noted that gcloud component updates are available.
- `./device/esp32/scripts/flash_esp32.sh --test-camera-platform --dry-run`: PASS. It printed PlatformIO build/upload commands and did not build, upload, or open a monitor.
- The same three commands were run successfully from `/tmp` using absolute script paths, confirming the helper scripts do not depend on the current working directory.
- Initial migration prep found path-dependent Node resolution on the current machine. The final pre-commit audit below resolved this by pinning Node major `22` in `.nvmrc` and package `engines`.

Full validation command set:

```bash
scripts/validate_repo.sh --all
```

Needs verification:

- Full backend/web/mobile/provisioning/simulator/firmware validation results on the new computer.
- Hardware flash and serial monitor behavior on the new computer.

## 2026-06-26 Final Pre-Commit Migration Audit

Commands run:

```bash
scripts/validate_repo.sh --docs
scripts/setup_new_machine.sh --check
bash -n scripts/setup_new_machine.sh scripts/validate_repo.sh device/esp32/scripts/flash_esp32.sh
git diff --check
node -e "for (const p of ['platform/web/package.json','platform/mobile/package.json','provision_backend/package.json','platform/mobile/eas.json','platform/web/package-lock.json','platform/mobile/package-lock.json']) { JSON.parse(require('fs').readFileSync(p,'utf8')); console.log('ok', p); }"
rg -n '/Users/gary/plantOS' device/esp32/scripts/flash_esp32.sh || true
git ls-files --cached --others --exclude-standard -z | xargs -0 rg -l -I '(BEGIN (RSA|OPENSSH|PRIVATE)|PRIVATE KEY|AIza[0-9A-Za-z_-]{20,}|AKIA[0-9A-Z]{16}|[A-Za-z0-9_]*SECRET[A-Za-z0-9_]*=|[A-Za-z0-9_]*PASSWORD[A-Za-z0-9_]*=|service_account|client_secret)' || true
```

Flash-helper dry-run audit:

```bash
./device/esp32/scripts/flash_esp32.sh --port /dev/cu.audit --dry-run
./device/esp32/scripts/flash_esp32.sh --local --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --gcp --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-dht22 --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-moisture --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-actuators --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-camera --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-wifi --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-touch --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-button-led --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-espnow-master --port /dev/cu.audit --dry-run --monitor
./device/esp32/scripts/flash_esp32.sh --test-espnow-camera --port /dev/cu.audit --dry-run --monitor
/Users/gary/plantOS/device/esp32/scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.audit --dry-run
```

Results:

- Static validation: PASS.
- Setup check: PASS. Active Node `v22.22.2` matches pinned major `22`; gcloud reported SDK `565.0.0` and available component updates.
- Shell syntax checks: PASS.
- `git diff --check`: PASS.
- JSON parse check for package, EAS, and lock files: PASS.
- Flash-helper dry-runs for all previous target flags: PASS. No build, upload, monitor, or hardware access occurred.
- Absolute-path flash-helper dry run from `/tmp`: PASS.
- No hard-coded `/Users/gary/plantOS` path remains in `device/esp32/scripts/flash_esp32.sh`.
- Secret-pattern scan was filename-only and printed no secret values. Matches were placeholders or existing code/docs references requiring normal review, not newly exposed secret material.

Findings fixed during this audit:

- Added early flash-helper error for a missing `device/esp32/platformio.ini`.
- Treated `PLANTLAB_SERIAL_PORT` as an explicit serial-port selection.
- Pinned Node major `22` with `.nvmrc` and package `engines`.
- Updated `scripts/setup_new_machine.sh --check` to report Node pin compliance.
- Changed provisioning setup from `npm ci` to `npm install` because `provision_backend/package-lock.json` is not committed and the Dockerfile already uses `npm install --omit=dev`.

Follow-up continuation check:

- Removed stale wording from the initial migration-prep section that said no Node pin existed.
- Re-ran `scripts/validate_repo.sh --docs`, `scripts/setup_new_machine.sh --check`, `bash -n`, `git diff --check`, the filename-only secret-pattern scan, and the flash-helper target dry-run matrix. All passed.
