# Docker

Docker-related assets for PlantLab local development and Cloud Run deployment.

Files:

- `Dockerfile.platform`: builds the FastAPI platform backend image from the
  repository root context.
- `Dockerfile.platform.dockerignore`: Dockerfile-specific ignore rules for the
  platform backend image build.
- `docker-compose.local.yml`: local PostgreSQL, platform backend, and
  provisioning backend stack.
- `cloudbuild.platform.yaml`: Cloud Build config used by the Cloud Run
  deployment helper.

Run the local stack from the repository root:

```bash
docker compose --env-file platform/infra/env/.env.local -f platform/infra/docker/docker-compose.local.yml up --build
```

The local compose stack is intentionally development-only:

- `platform` listens on `http://localhost:8000`.
- `provision-backend` listens on `http://localhost:3000`.
- `PLANTLAB_DEV_TOKEN_AUTH_ENABLED=true` is set for local mobile username/password login.
- image URLs use the authenticated local proxy path instead of GCS signed URLs.
- container dotenv loading is disabled with `PLANTLAB_SKIP_DOTENV=1`; runtime values come from compose and `platform/infra/env/.env.local`.
- both backend services include Docker healthchecks.

For iPhone local QA, set `platform/mobile/.env` to the Mac LAN URL, for example:

```bash
EXPO_PUBLIC_API_BASE_URL=http://192.168.0.55:8000
EXPO_PUBLIC_AUTH_MODE=dev
EXPO_PUBLIC_ENABLE_DEV_AUTH=true
EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false
```
