# Migration Inventory

Last updated: 2026-06-26.

This inventory separates what Git should restore from what must be recreated,
backed up securely, or kept out of the repository.

## A. Restored By Git

These paths are intended to be version-controlled and restored by a normal clone:

- `AGENTS.md`
- `CURRENT_STATE.md`
- `.nvmrc`
- `.env.example`
- `.env.local.example`
- `contracts/`
- `device/esp32/`
- `docs/`
- `platform/backend/`
- `platform/web/`
- `platform/mobile/`
- `platform/infra/`
- `provision_backend/`
- `scripts/`
- `tools/simulator/`
- `package-lock.json` files in package directories.
- `platform/backend/data/uploads/.gitkeep`
- Small demo assets under `platform/web/src/assets/demo/`, including the current
  demo growth video.

No Git LFS tracked files were found with `git lfs ls-files`.

## B. Git LFS Or External Artifact Storage

Git LFS is not currently configured. Use Git LFS or an external artifact store
if these assets must be versioned:

- Large videos.
- Raw image or camera-quality datasets.
- CAD files, renders, manufacturing packages, and hardware export bundles.
- Firmware release binaries.
- Long validation recordings.
- Trained models or generated datasets.

Current largest tracked files are still small enough for normal Git, with the
largest verified file being `platform/web/src/assets/demo/growth-timelapse.mp4`
at about 808 KB.

## C. Back Up Separately And Securely

These files and folders should not be committed. Back them up through a secure
password manager, cloud secret store, or encrypted backup when needed:

- Real `.env` and `.env.local` files.
- Real `platform/infra/env/.env*` files.
- Real `platform/web/.env` and `platform/mobile/.env` files.
- Real `provision_backend/.env` files.
- `device/esp32/include/platform_secrets.h`.
- Google Cloud CLI auth state such as `~/.config/gcloud`.
- EAS, Apple Developer, signing certificates, provisioning profiles, and API
  keys.
- Root runtime data currently verified under `data/`:
  - `data/demo-account-local.db`
  - `data/uploads/`
  - `data/demo-account-uploads/`
- Local backend runtime data such as `platform/backend/data/*.db` and uploads.
- Docker volumes containing local Postgres or object data.
- Private calibration files, manufacturing notes, or board-specific credentials
  not already committed intentionally.

## D. Safe To Recreate

These are dependency caches or generated outputs and should not be migrated by
hand unless debugging a very specific local issue:

- `.venv/`
- `node_modules/`
- `.pio-core/`
- `device/esp32/.pio/`
- `platform/web/dist/`
- `platform/mobile/dist/`
- Python `__pycache__/` and `.pytest_cache/`
- Docker image cache.
- `.DS_Store` and temporary files.

## E. New-Machine Access Checklist

Verify these before expecting full repository workflows to pass:

- GitHub SSH access to `git@github.com:firedonkey/plantOS.git`.
- Google Cloud CLI installed, authenticated, and pointed at the intended project.
- IAM permissions for Cloud Run, Cloud Build, Artifact Registry, Cloud SQL,
  Secret Manager, and logging.
- Secret Manager values available for backend and provisioning deployments.
- Docker Desktop or Docker Engine.
- Python 3 with `venv`.
- Node.js 22 and npm. Use `.nvmrc` or `scripts/setup_new_machine.sh --check`
  to verify the active major version.
- PlatformIO CLI, preferably installed by `scripts/setup_new_machine.sh --python`.
- Xcode and iOS simulator tooling for mobile work on macOS.
- EAS CLI and Apple Developer access for mobile build workflows.
- USB serial permissions/drivers:
  - macOS: `/dev/cu.usbmodem*` and `/dev/cu.usbserial*`
  - Linux/Jetson: `/dev/ttyACM*` and `/dev/ttyUSB*`

## F. Hardware Validation Checklist

After moving computers, validate hardware behavior on the bench before treating
the setup as production-ready:

- Confirm PCB revision and wiring against `device/esp32/include/config.h`.
- Confirm ESP32 master serial connection and flash port.
- Confirm XIAO ESP32S3 camera serial connection and flash port.
- Confirm water level sensor wiring and touch thresholds.
- Confirm soil moisture calibration.
- Confirm MCP9808 water-temperature behavior on the main I2C bus.
- Confirm status LED and grow-light MOSFET behavior.
- Confirm ESP-NOW master/camera link.
- Confirm OV3660 image quality after the camera swap-back.
- Confirm OV5640/DC5640-AF autofocus and image-quality behavior before using it
  as the main camera path.

## Data Usage Classification

Must commit:

- Source, tests, docs, migrations, schemas, generated contract artifacts, and
  package lockfiles.
- `platform/backend/data/uploads/.gitkeep`.
- Small demo assets under `platform/web/src/assets/demo/` that are required by
  the checked-in web app.
- Future small fixtures only when placed under explicit fixture directories.

Use Git LFS or separate backup:

- Large videos.
- Raw images and camera datasets.
- CAD files and generated renders.
- Firmware binaries.
- Manufacturing exports.
- Trained models.

Ignore:

- Root `data/*.db`, `data/uploads/`, and `data/demo-account-uploads/`.
- Local backend DB/upload runtime data.
- Caches, dependency folders, build outputs, and virtual environments.
- Real env files and hardware secret headers.
