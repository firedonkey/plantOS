# Platform Migration Plan

## Final goal

Real separation between backend and frontend.

Final architecture:

- `platform/backend` = API only
- `platform/web` = standalone frontend app
- `platform/mobile` = Expo app
- `platform/shared` = contracts, docs, shared types
- `platform/infra` = deployment and dev scripts

## Target structure

```text
platform/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      webhooks/
      main.py
    migrations/
    tests/
    Dockerfile
    requirements.txt
    README.md

  web/
    app/
    src/
      api/
      components/
      hooks/
      routes/
      screens/
      styles/
      types/
    public/
    package.json
    README.md

  mobile/
    app/
    src/
      api/
      components/
      hooks/
      screens/
      storage/
      types/
      mock/
    assets/
    app.json
    package.json
    README.md
    MOBILE_APP_PLAN.md

  shared/
    openapi/
    types/
    docs/
    README.md

  infra/
    cloud-run/
    docker/
    scripts/
    README.md

  README.md
```

## Stage 1: Safe move

Purpose:

- move current code into the new structure safely
- keep the existing web app working
- clean up repo structure without breaking current behavior

Rules:

- it is acceptable if the current server-rendered web still lives inside `backend` temporarily
- do not remove or rewrite working web pages yet
- backend may still serve web routes, templates, and static assets during this stage
- keep `requirements.txt`
- this stage is **not** the final architecture

Stage 1 tasks:

1. Move `platform/app` -> `platform/backend/app`
2. Move `platform/migrations` -> `platform/backend/migrations`
3. Move `platform/tests` -> `platform/backend/tests`
4. Update imports, local run scripts, test commands, and Dockerfile paths
5. Keep the current web routes and templates working through backend
6. Confirm current local backend and current web behavior still work

Stage 1 success criteria:

- local backend still runs
- `/health` still works
- current website still works
- tests still run
- repo structure is cleaner, even though backend and web are not fully separated yet

## Stage 2: Real separation

Purpose:

- move or rebuild the web frontend into `platform/web`
- make `platform/backend` API-only
- make both web and mobile use the same backend API endpoints

Rules:

- create or rebuild the frontend app in `platform/web`
- web should communicate with backend only through API endpoints
- mobile should also use the same API endpoints
- do not delete backend-rendered web routes until `platform/web` fully replaces them
- `shared/` should hold OpenAPI schemas, shared API docs, and later generated TypeScript types

Stage 2 tasks:

1. Create the standalone frontend app in `platform/web`
2. Move frontend logic out of backend
3. Replace server-rendered flows with API-backed frontend flows
4. Make backend API-only
5. Retire old server-rendered routes only after replacement behavior is working

Stage 2 success criteria:

- `platform/web` works as the user website/dashboard
- `platform/backend` serves API only
- `platform/mobile` can consume the same API surface
- shared contracts and types have a clear home under `platform/shared`

## Revised preferred order

1. Architecture doc
2. Inventory current backend/web coupling
3. Stage 1 safe move
   - `platform/app -> platform/backend/app`
   - `platform/migrations -> platform/backend/migrations`
   - `platform/tests -> platform/backend/tests`
   - update imports, scripts, and Dockerfile paths
   - confirm current web still works
4. Define standalone API contract for web and mobile
5. Add token/mobile-ready auth support
6. Scaffold `platform/mobile` with Expo
7. Stage 2 real separation
   - create or rebuild `platform/web`
   - move frontend logic out of backend
   - make backend API-only
   - retire old server-rendered routes only after replacement works
8. Add shared OpenAPI, docs, and types
9. Clean local dev scripts
10. Plan GCP deployment changes later

Important:

- do not treat Stage 1 as the final architecture
- Stage 1 is only a safe transition
- the final goal is real separation between backend and frontend
- do local server work first
- do not change GCP during this migration work

## Migration implementation rules

These rules apply during the migration work and should be treated as hard guardrails:

1. Add tests or smoke tests for each step.
2. If tests pass, commit immediately.
3. Stage 1 must not change behavior.
4. The system must remain runnable at all times.
5. Never delete old functionality before replacement works.
6. Use small commits, one logical change per commit.
7. Define pass criteria before each step.
8. Log key flows during migration.
9. Avoid business-logic refactors during structure changes.
10. Keep rollback easy using git.
11. Preserve `/health` for quick verification at all times.
12. Stabilize API before building mobile.

## Step execution template

For every migration step:

1. Define the exact change.
2. Define pass criteria before editing code.
3. Add or identify the test or smoke check for that step.
4. Make the smallest change needed.
5. Run verification immediately.
6. If the step passes, commit immediately.
7. Only then move to the next step.

## Required verification checks

At a minimum, keep these checks working throughout migration:

- backend starts locally
- `/health` returns success
- current web flow still works during Stage 1
- tests for the touched area pass
- key user flows remain observable through logs

## Logging expectations during migration

Keep enough logging to verify these flows quickly:

- backend boot/startup
- database init or migration startup
- `/health` checks
- dev-only auth/login path used for local development
- device list fetch
- device detail fetch
- command submission
- setup/provisioning flow where applicable

The goal is not to add noisy logging everywhere. The goal is to make breakage obvious during the move.

## Commit discipline

- prefer one logical change per commit
- commit immediately after a step passes
- avoid mixing file moves with unrelated logic changes
- keep every step easy to revert

## Stage 1 guardrails

During Stage 1:

- do not change behavior intentionally
- do not delete current server-rendered routes
- do not rewrite working web pages
- do not refactor business logic just because files are moving
- keep `requirements.txt`
- keep the current system runnable locally throughout

## Stage 2 guardrails

During Stage 2:

- build the standalone `platform/web` first
- do not remove old backend-rendered routes until replacement works
- make backend API-only only after the standalone web is verified
- stabilize API behavior before relying on it from mobile

## Auth note

Any placeholder token auth added during the migration should be treated as **dev-only**.

That means:

- use it only to unblock local standalone web and mobile development
- do not treat it as production auth
- keep real production auth work separate from the structure migration
