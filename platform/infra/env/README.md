# PlantLab Infra Environment Files

This folder is the local home for ignored environment files used by deployment
and local infrastructure workflows.

Expected local files:

- `.env`
- `.env.local`

These files may contain secrets and must stay untracked. Use the examples in
the repository root as templates, then keep real values in this folder.

Deployment helper usage:

- Put backend deployment values in `.env`.
- Keep `.env.local` for local Docker and direct development flows.
- `deploy_backend.sh` reads only `.env`.

Minimum non-secret backend deployment values:

```bash
GOOGLE_OAUTH_CLIENT_ID="<oauth-client-id>"
PLANTLAB_LOCAL_SETUP_URL="http://10.42.0.1:8080/"
PLANTLAB_DEVICE_PLATFORM_URL="<production-api-url-or-custom-domain>"
PLANTLAB_STANDALONE_WEB_ORIGIN_REGEX="<exact-production-web-origin-regex>"
```

Secret values should stay in Secret Manager for Cloud Run deployment. The
backend deployment script references Secret Manager names instead of passing
secret values through `gcloud run deploy`.

Compatibility notes:

- `platform/infra/cloud-run/deploy_backend.sh` loads `.env` from this folder
  automatically.
- `platform/backend/app/core/settings.py` also loads these files for direct
  backend runs.
- `platform/infra/docker/docker-compose.local.yml` can read this folder through:

  ```bash
  docker compose --env-file platform/infra/env/.env.local -f platform/infra/docker/docker-compose.local.yml up
  ```
