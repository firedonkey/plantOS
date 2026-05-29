# Backend

This folder contains the PlantLab FastAPI backend.

Stage 1 status:

- the backend code has been moved here for safer structure separation
- the current server-rendered web is still temporarily served by the backend
- this is a transition state, not the final architecture

Current local run flow:

```bash
cd platform/backend
source ../../.venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

Local Docker demo flow:

```bash
cd /Users/gary/plantOS
docker compose -f platform/infra/docker/docker-compose.local.yml up -d --build platform
```

The Docker `platform` service runs local database bootstrap/migrations before
starting the backend, so schema changes are applied to the local Postgres
volume during restart.

Current local test flow:

```bash
cd platform/backend
source ../../.venv/bin/activate
python -m pytest tests
```

Quick verification pointers:

- health check: [http://localhost:8000/health](http://localhost:8000/health)
- old backend-rendered login: [http://localhost:8000/login](http://localhost:8000/login)
- standalone Google auth start: [http://localhost:8000/api/auth/google/start?client=web&return_to=http%3A%2F%2Flocalhost%3A5173%2Flogin](http://localhost:8000/api/auth/google/start?client=web&return_to=http%3A%2F%2Flocalhost%3A5173%2Flogin)
- standalone Apple auth start: `http://localhost:8000/api/auth/apple/start?client=web&return_to=http%3A%2F%2Flocalhost%3A5173%2Flogin` after configuring `PLANTLAB_APPLE_WEB_CLIENT_ID` with the Apple Services ID used for web sign-in. Native mobile Apple sign-in continues to use `PLANTLAB_APPLE_CLIENT_ID`.
- one-command local status check:

```bash
cd /Users/gary/plantOS
.venv/bin/python platform/infra/scripts/local_status_check.py
```
