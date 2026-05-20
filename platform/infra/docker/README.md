# Docker

Docker-related assets for PlantLab local development and Cloud Run deployment.

Files:

- `Dockerfile.platform`: builds the FastAPI platform backend image from the
  repository root context.
- `Dockerfile.platform.dockerignore`: Dockerfile-specific ignore rules for the
  platform backend image build.
- `Dockerfile.web`: builds the standalone Vite web frontend and serves the
  production bundle with `vite preview`.
- `Dockerfile.web.dockerignore`: Dockerfile-specific ignore rules for the web
  image build.
- `Dockerfile.admin`: serves the separate static admin diagnostics frontend.
- `Dockerfile.admin.dockerignore`: Dockerfile-specific ignore rules for the admin
  frontend image build.
- `docker-compose.local.yml`: local PostgreSQL, platform backend, and
  provisioning backend stack, plus the standalone web and admin frontends.
- `cloudbuild.platform.yaml`: Cloud Build config used by the Cloud Run
  deployment helper.

Run the local stack from the repository root:

```bash
docker compose --env-file platform/infra/env/.env.local -f platform/infra/docker/docker-compose.local.yml up --build
```

The local compose stack is intentionally development-only:

- `platform` listens on `http://localhost:8000`.
- `web` listens on `http://localhost:5173`.
- `admin-web` listens on `http://localhost:5174`.
- `provision-backend` listens on `http://localhost:3000`.
- `PLANTLAB_DEV_TOKEN_AUTH_ENABLED=true` is set for local mobile username/password login.
- `PLANTLAB_ADMIN_EMAILS=dev@plantlab.local` is set for local admin diagnostics.
- the web frontend is built with dev auth enabled and `VITE_API_BASE_URL=http://localhost:8000` by default.
- image URLs use the authenticated local proxy path instead of GCS signed URLs.
- container dotenv loading is disabled with `PLANTLAB_SKIP_DOTENV=1`; runtime values come from compose and `platform/infra/env/.env.local`.
- the `platform` service runs local database bootstrap/migrations before
  starting Uvicorn, so existing Postgres volumes get new backend columns.
- backend, provisioning, and web services include Docker healthchecks.

Open the Dockerized web frontend:

```bash
open http://localhost:5173
```

Open the local admin diagnostics frontend:

```bash
open http://localhost:5174
```

Use the local dev login:

```text
dev@plantlab.local
password
```

Override the frontend API URL at build time when needed:

```bash
VITE_API_BASE_URL=http://192.168.0.55:8000 \
docker compose -f platform/infra/docker/docker-compose.local.yml up -d --build web
```

Apply backend schema changes to the local Docker database:

```bash
docker compose -f platform/infra/docker/docker-compose.local.yml up -d --build platform
```

Check the migration state:

```bash
docker exec plantlab-local-postgres psql -U plantlab_user -d plantlab -c "SELECT * FROM alembic_version;"
```

For iPhone local QA, set `platform/mobile/.env` to the Mac LAN URL, for example:

```bash
EXPO_PUBLIC_API_BASE_URL=http://192.168.0.55:8000
EXPO_PUBLIC_AUTH_MODE=dev
EXPO_PUBLIC_ENABLE_DEV_AUTH=true
EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=false
```
