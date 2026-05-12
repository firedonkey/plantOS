# Auth Migration Plan

## Purpose

This document tracks how PlantLab should move from the current mixed auth state to a production-ready shared auth model for:

- old backend-rendered web
- standalone `platform/web`
- `platform/mobile`

The goal is to retire old `/login` only after standalone web and mobile both have a supported production auth path.

## Current state

### Old backend-rendered web

- Uses browser session auth.
- Uses Google OAuth through:
  - `GET /auth/login`
  - `GET /auth/callback`
  - `POST /auth/logout`
- Old pages like `/login`, `/devices`, and `/devices/{id}` assume session cookies.

### Standalone web

- Uses `POST /api/auth/login`.
- Stores a bearer token in local storage.
- Calls `GET /api/me` to verify the token.
- This is explicitly **dev-only** local auth.

### Mobile

- Uses the same dev-only bearer auth path as standalone web.
- Stores the token locally and uses `Authorization: Bearer ...`.
- Also explicitly **dev-only** today.

## Target production auth

We want one production-ready auth contract shared by standalone web and mobile, while preserving a safe migration path.

### Preferred target

1. Keep Google as the primary identity provider.
2. Add backend-issued API auth for standalone clients after Google identity is established.
3. Let standalone web and mobile use backend-issued tokens instead of session-only auth.

That gives us:

- old backend-rendered web: Google + session during migration
- standalone web: Google sign-in + backend token/session exchange
- mobile: backend token after browser-based or app-based Google sign-in handoff

## Web auth migration path

Recommended path:

1. Keep old `/login` and old Google session auth working.
2. Add a standalone-web production sign-in entry that starts real Google auth.
3. After Google callback, issue a standalone-compatible auth credential for `platform/web`.
4. Update standalone web to stop depending on dev-only login.
5. Verify all protected standalone routes with the production auth path.
6. Only then mark old `/login` as removable.

### Acceptable implementation shapes later

Any of these can work, as long as the contract is clear:

- secure HTTP-only cookie for standalone web
- short-lived bearer token + refresh mechanism
- session exchange endpoint that converts Google callback state into a standalone-web auth state

We should choose the safest option that preserves backend ownership of auth.

## Mobile auth migration path

Recommended path:

1. Reuse the same backend identity model as standalone web.
2. Support a mobile-friendly Google sign-in entry.
3. Exchange the verified identity for backend-issued API credentials.
4. Store those credentials in mobile storage.
5. Use the same protected API surface as standalone web.

The important point is that mobile should not get a separate business logic auth stack. It should share the same backend auth contract.

## Old `/login` retirement gate

Old `/login` is not safe to retire until all of the following are true:

1. Standalone web has production-ready auth.
2. Standalone web routes work end to end without the old login page.
3. Mobile has a documented production auth path using the same backend contract.
4. We no longer rely on backend-rendered session-only pages for core user flows.
5. Local and production rollout plans are clear.

Until then:

- keep old `/login`
- keep old Google session auth
- keep the standalone dev-only auth clearly marked as temporary

## What stays dev-only for now

These are temporary and should not be mistaken for the production plan:

- `POST /api/auth/login`
- local-storage bearer tokens in standalone web
- mobile local bearer login using the same endpoint

## Recommended next auth step

Do **not** replace auth during structure cleanup.

The safest next auth milestone is:

1. choose the production standalone-web auth shape
2. document the callback/token exchange contract
3. implement standalone web production auth behind the existing backend
4. then bring mobile onto the same contract
