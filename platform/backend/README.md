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

Current local test flow:

```bash
cd platform/backend
source ../../.venv/bin/activate
python -m pytest tests
```
