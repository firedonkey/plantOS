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
