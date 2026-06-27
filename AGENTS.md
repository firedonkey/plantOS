# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Scope Rules

- Do not change product behavior, firmware behavior, APIs, hardware settings, migrations, or deployment scripts unless the user explicitly asks for that change.
- Read `CURRENT_STATE.md` before starting migration, setup, deployment, or hardware tasks.
- Use `docs/MIGRATION_INVENTORY.md` when deciding whether a file belongs in Git, Git LFS, secure backup, or local ignore rules.
- Before editing, run `git status --short` and identify unrelated local changes. Do not revert or stage unrelated files.
- Treat files under `data/`, `.env*`, `platform/infra/env/.env*`, `device/esp32/include/platform_secrets.h`, build output, `.pio*`, `node_modules`, and `.venv` as local-only unless the user explicitly says otherwise.
- Prefer small, targeted edits that follow existing patterns in the repo.
- For firmware work, verify the relevant PlatformIO environment in `device/esp32/platformio.ini` before changing code or flash commands.

## Repository Map

- `contracts/`: JSON Schemas, examples, and generated firmware/TypeScript/Python contract artifacts.
- `device/esp32/`: ESP32-S3 master and XIAO ESP32S3 camera firmware, PlatformIO environments, and flash helper.
- `docs/`: architecture, protocol, setup, validation, and reliability notes.
- `platform/backend/`: FastAPI backend, Alembic migrations, SQLAlchemy models, services, routes, and pytest tests.
- `platform/web/`: Vite React web app.
- `platform/mobile/`: Expo React Native app.
- `platform/infra/`: Docker, Cloud Run deployment helpers, local status scripts, OTA release tools, and env docs.
- `provision_backend/`: Node/Express provisioning API.
- `tools/simulator/`: protocol simulator and smoke tests.

## Standard Checks

Use the smallest relevant set for the files changed:

```bash
git diff --check
.venv/bin/pytest platform/backend/tests -q
node --test platform/web/test/*.test.js
npm --prefix platform/web run typecheck
npm --prefix platform/web run build
npm --prefix platform/mobile run typecheck
npm --prefix platform/mobile run test:unit
npm --prefix provision_backend test
.venv/bin/pytest tools/simulator/test_simulator_smoke.py -q
.venv/bin/pio run -d device/esp32 -e esp32-local
.venv/bin/pio run -d device/esp32 -e camera-platform-test
```

The helper script `scripts/validate_repo.sh` can run these groups reproducibly.

## Git Hygiene

- Commit source, docs, migrations, contract schemas/generated artifacts, package lockfiles, and small intentional demo assets.
- Do not commit secrets, local databases, uploads, virtual environments, dependency folders, PlatformIO build folders, Cloud Run deploy state, serial logs, firmware binaries, or private keys.
- No Git LFS tracking is currently configured. Use Git LFS for future large media, firmware binaries, hardware captures, or generated datasets that must be versioned.

## Hardware Safety

- Do not flash hardware unless requested.
- Use `device/esp32/scripts/flash_esp32.sh --dry-run` to inspect firmware commands. Real upload requires `--flash`.
- Do not alter pin mappings, board environments, OTA behavior, provisioning behavior, or camera sensor tuning unless requested.
- The current OV5640 autofocus camera work is saved as WIP and needs more validation before being treated as production-ready.
