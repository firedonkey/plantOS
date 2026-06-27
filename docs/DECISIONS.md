# Decisions

This file is a migration-friendly index of verified decisions. The older append-only log remains at `docs/decision_log.md`.

## Verified Decisions

### Repository Structure

- Current device work is under `device/esp32/`; the legacy Raspberry Pi runtime has been removed.
- Backend code is under `platform/backend/`.
- Standalone web is under `platform/web/`.
- Mobile is under `platform/mobile/`.
- Provisioning backend is under `provision_backend/`.
- Shared contracts are under `contracts/`.

### Device Protocol

- Device protocol schemas and generated artifacts live under `contracts/`.
- Firmware includes generated contract constants at `contracts/generated/firmware/plantlab_contracts.h` and `device/esp32/include/contracts/plantlab_contracts.h`.
- Backend tests include contract tests under `platform/backend/tests/contracts/`.

### Auth And Demo

- Backend-owned standalone auth exists for web/mobile.
- Demo-account support exists in backend, web, and mobile code.
- Demo users are marked by `is_demo_user` in the backend user model.

### Deployment

- Backend Cloud Run deployment uses `platform/infra/cloud-run/deploy_backend.sh`.
- Provisioning Cloud Run deployment uses `platform/infra/cloud-run/deploy_provisioning_backend.sh`.
- Backend production deploys run build, backup, migration, candidate deploy, health verification, then explicit traffic shift.
- Secret values should be supplied through Secret Manager for Cloud Run, not committed env files.
- Web deployment has Cloud Build/Docker config in `platform/infra/docker/`, but no verified dedicated deployment helper in the repository.

### Firmware Tooling

- `device/esp32/scripts/flash_esp32.sh` resolves the repo path from the script location.
- The flash helper defaults to dry-run/check mode.
- Real hardware upload requires explicit `--flash`.
- If multiple serial ports are detected, the helper requires `--port` before flashing.

### Version Control

- `package-lock.json` files are version-controlled for web and mobile.
- Contract generated artifacts are version-controlled.
- Small demo media assets are currently version-controlled.
- Git LFS is not currently configured.
- Root runtime data is ignored with precise rules for local DB and upload paths, not a broad `data/` ignore.

### Node Tooling

- Node major `22` is pinned in `.nvmrc`.
- Web, mobile, and provisioning package manifests declare `node >=22 <23`.
- Web, admin, and provisioning Dockerfiles use Node 22 base images.
- `provision_backend` does not currently commit a `package-lock.json`; setup uses `npm install` there and `npm ci` for web/mobile.

## Needs Verification

- Whether web deployment should get a dedicated helper script after the exact workflow is verified.
- Whether future large demo videos/images should move to Git LFS.
- Whether OV5640 autofocus support should remain in the current firmware path or be isolated behind a separate environment after bench testing.
- Whether root `data/` is the only local runtime state created by demo/local testing.
