# Platform

This folder contains the PlantLab platform code and the migration toward a clean split between backend, web, mobile, shared contracts, and infrastructure.

Start here:

- [Migration Plan](/Users/gary/plantOS/platform/MIGRATION_PLAN.md)

Current intent:

- `backend/` will become the API server
- `web/` will become the standalone browser frontend
- `mobile/` will hold the Expo app
- `shared/` will hold OpenAPI, docs, and shared types
- `infra/` will hold scripts and deployment assets

During Stage 1, the current runnable backend and server-rendered web may still temporarily live in the legacy layout while files are being moved safely.
