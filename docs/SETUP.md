# Setup

This is the migration setup guide for a new development computer.

## Prerequisites

Verified repository tooling categories:

- Git
- Python 3 with `venv`
- Node.js 22 and npm
- Docker Desktop or compatible Docker Engine
- Google Cloud CLI, for deployment
- PlatformIO CLI, installed in the repo virtualenv by the setup helper
- EAS CLI, for mobile cloud builds

macOS:

- Xcode and iOS simulator are required for local iOS/mobile work.
- ESP32 serial devices normally appear as `/dev/cu.usbmodem*` or
  `/dev/cu.usbserial*`.
- Docker Desktop is the expected Docker runtime.

Linux:

- Docker Engine is expected.
- The user may need membership in `docker` and `dialout` groups.
- ESP32 serial devices normally appear as `/dev/ttyACM*` or `/dev/ttyUSB*`.

Jetson:

- Needs verification. Treat Jetson setup like Linux, but verify Python, Node,
  Docker, and PlatformIO availability before assuming firmware builds work.

Needs verification:

- Exact Python minor version. The current local `.venv` has run tests with
  Python 3.14, while the Cloud Run backend image uses Python 3.12.
- Xcode/iOS simulator setup for mobile development.
- USB serial driver behavior for ESP32 boards.

## Clone

```bash
git clone git@github.com:firedonkey/plantOS.git
cd plantOS
git status --short
```

Commands below assume they are run from the repo root unless they explicitly
`cd` elsewhere. If the clone path is different, no script should require editing
solely because of the path.

## Environment Files

Do not copy real secrets into Git.

Template files:

- `.env.example`
- `.env.local.example`
- `platform/web/.env.example`
- `platform/mobile/.env.example`
- `provision_backend/.env.example`
- `device/esp32/include/platform_secrets.example.h`

Local files that may contain secrets and must stay untracked:

- `.env`
- `.env.local`
- `platform/infra/env/.env`
- `platform/infra/env/.env.local`
- `platform/web/.env`
- `platform/mobile/.env`
- `provision_backend/.env`
- `device/esp32/include/platform_secrets.h`

Create local templates:

```bash
cp .env.example .env
cp .env.local.example platform/infra/env/.env.local
cp platform/web/.env.example platform/web/.env
cp platform/mobile/.env.example platform/mobile/.env
cp provision_backend/.env.example provision_backend/.env
cp device/esp32/include/platform_secrets.example.h device/esp32/include/platform_secrets.h
```

Then edit the copied files locally. Do not commit them.

The helper can create only missing local files from examples:

```bash
scripts/setup_new_machine.sh --env
```

## Install Dependencies

Inspect local tooling without installing anything:

```bash
scripts/setup_new_machine.sh --check
```

Node version:

- `.nvmrc` pins Node major `22`.
- `platform/web/package.json`, `platform/mobile/package.json`, and
  `provision_backend/package.json` declare `node >=22 <23`.
- The active Dockerfiles for web, admin, and provisioning also use Node 22.
- `scripts/setup_new_machine.sh --check` reports whether the active Node major
  matches the pin.

Python/backend/firmware:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r platform/backend/requirements.txt
.venv/bin/python -m pip install platformio
```

Node workspaces:

```bash
npm --prefix platform/web ci
npm --prefix platform/mobile ci
npm --prefix provision_backend install
```

`provision_backend` does not currently have a committed `package-lock.json`, so
it uses `npm install`. The web and mobile packages have committed lockfiles and
use `npm ci`.

Or use the setup helper:

```bash
scripts/setup_new_machine.sh --all
```

The helper prints what it will install, generate, or modify before running. It
does not install system tools and does not write real secrets.

## Local Development

Docker stack:

```bash
docker compose -f platform/infra/docker/docker-compose.local.yml up --build
```

Direct backend:

```bash
cd platform/backend
../../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Web:

```bash
npm --prefix platform/web run dev
```

Mobile:

```bash
npm --prefix platform/mobile run start
npm --prefix platform/mobile run start:dev:local -- --host lan
```

Provisioning backend:

```bash
npm --prefix provision_backend run dev
```

## Validation Commands

Static docs/script validation:

```bash
scripts/validate_repo.sh --docs
```

Full local validation:

```bash
scripts/validate_repo.sh --all
```

Individual checks:

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

## Firmware Build And Flash

Build only:

```bash
.venv/bin/pio run -d device/esp32 -e esp32-local
.venv/bin/pio run -d device/esp32 -e esp32-gcp
.venv/bin/pio run -d device/esp32 -e camera-platform-test
.venv/bin/pio run -d device/esp32 -e camera-test
.venv/bin/pio run -d device/esp32 -e espnow-master-test
.venv/bin/pio run -d device/esp32 -e espnow-camera-test
```

Portable flash helper:

```bash
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --dry-run
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --build-only
./device/esp32/scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem12201 --flash --monitor
./device/esp32/scripts/flash_esp32.sh --local --port /dev/cu.usbmodem11401 --flash
```

The helper defaults to `--dry-run`. It does not flash hardware unless `--flash`
is passed.

Previous flash-helper workflow equivalents:

| Previous command | New intentional command |
| --- | --- |
| `./device/esp32/scripts/flash_esp32.sh` | `./device/esp32/scripts/flash_esp32.sh --port /dev/cu.usbmodem11401 --flash` |
| `./device/esp32/scripts/flash_esp32.sh --monitor` | `./device/esp32/scripts/flash_esp32.sh --port /dev/cu.usbmodem11401 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --local --monitor` | `./device/esp32/scripts/flash_esp32.sh --local --port /dev/cu.usbmodem11401 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --gcp --monitor` | `./device/esp32/scripts/flash_esp32.sh --gcp --port /dev/cu.usbmodem11401 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-dht22 --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-dht22 --port /dev/cu.usbmodem11401 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-moisture --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-moisture --port /dev/cu.usbmodem11401 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-actuators --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-actuators --port /dev/cu.usbmodem11401 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-camera --port /dev/cu.usbmodem12201 --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-camera --port /dev/cu.usbmodem12201 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem12201 --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-camera-platform --port /dev/cu.usbmodem12201 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-wifi --port /dev/cu.usbmodem12201 --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-wifi --port /dev/cu.usbmodem12201 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-touch --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-touch --port /dev/cu.usbmodem11401 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-button-led --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-button-led --port /dev/cu.usbmodem11401 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-espnow-master --port /dev/cu.usbmodem1301 --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-espnow-master --port /dev/cu.usbmodem1301 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --test-espnow-camera --port /dev/cu.usbmodem12201 --monitor` | `./device/esp32/scripts/flash_esp32.sh --test-espnow-camera --port /dev/cu.usbmodem12201 --flash --monitor` |
| `./device/esp32/scripts/flash_esp32.sh --port /dev/cu.usbmodem1301 --monitor` | `./device/esp32/scripts/flash_esp32.sh --port /dev/cu.usbmodem1301 --flash --monitor` |

## Deployment Commands

Backend:

```bash
platform/infra/cloud-run/deploy_backend.sh print-config
platform/infra/cloud-run/deploy_backend.sh preflight
platform/infra/cloud-run/deploy_backend.sh test-local
platform/infra/cloud-run/deploy_backend.sh build
platform/infra/cloud-run/deploy_backend.sh backup
platform/infra/cloud-run/deploy_backend.sh migrate
platform/infra/cloud-run/deploy_backend.sh deploy-candidate
VERIFY_URL="<candidate-url>" platform/infra/cloud-run/deploy_backend.sh verify-health
CONFIRM_SHIFT_TRAFFIC=yes platform/infra/cloud-run/deploy_backend.sh shift-traffic
```

Provisioning backend:

```bash
platform/infra/cloud-run/deploy_provisioning_backend.sh print-config
platform/infra/cloud-run/deploy_provisioning_backend.sh preflight
platform/infra/cloud-run/deploy_provisioning_backend.sh test-local
platform/infra/cloud-run/deploy_provisioning_backend.sh build
platform/infra/cloud-run/deploy_provisioning_backend.sh deploy-candidate
VERIFY_URL="<candidate-url>" platform/infra/cloud-run/deploy_provisioning_backend.sh verify-health
CONFIRM_SHIFT_TRAFFIC=yes platform/infra/cloud-run/deploy_provisioning_backend.sh shift-traffic
```

Web:

- Known: `platform/infra/docker/cloudbuild.web.yaml` and
  `platform/infra/docker/Dockerfile.web` exist.
- Needs verification: exact production web deployment command and whether it
  should be wrapped in a dedicated helper. No helper was added during migration
  prep because deployment behavior was out of scope.

## Version-Control Policy

Should be version-controlled:

- Source files.
- Tests.
- Docs.
- Migrations.
- Contract schemas and generated contract artifacts.
- `package-lock.json`.
- Small intentional demo assets currently used by the app.

Should use Git LFS or external artifact storage if they must be versioned:

- Large videos.
- Large image sets.
- Firmware release binaries.
- Hardware capture datasets.
- CAD/renders/manufacturing exports.
- Long validation recordings.

Must never be committed:

- Real `.env` values.
- API keys, OAuth secrets, passwords, private keys, service account JSON files.
- `device/esp32/include/platform_secrets.h`.
- Local SQLite/Postgres data and uploads.
- `.venv/`, `node_modules/`, `.pio-core/`, `device/esp32/.pio/`.
- Cloud Run deploy state files under `platform/infra/cloud-run/`.
- Serial logs and stress-test output that contain tokens or local network data.
