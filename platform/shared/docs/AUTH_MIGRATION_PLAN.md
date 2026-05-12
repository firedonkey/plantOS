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

## Proposed production auth contract

Backend remains the single auth owner.

### Identity source

- Google remains the primary identity provider.
- Backend validates Google identity and issues PlantLab-controlled standalone credentials.

### Proposed standalone auth endpoints

These are the recommended production endpoints to implement next:

- `GET /api/auth/google/start`
- `GET /api/auth/google/callback`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/me`

### Endpoint responsibilities

#### `GET /api/auth/google/start`

Purpose:

- start Google sign-in for standalone clients
- support web directly
- support mobile via browser/session handoff

Recommended request inputs:

- optional `return_to`
- optional `client` with values like `web` or `mobile`

Recommended behavior:

- create OAuth state under backend control
- redirect to Google

#### `GET /api/auth/google/callback`

Purpose:

- receive Google callback
- resolve or create the user in PlantLab
- issue backend-owned standalone credentials

Recommended behavior for standalone web:

- set a secure refresh cookie
- redirect to the standalone frontend with a short-lived access token exchange path or a completed session state

Recommended behavior for mobile:

- return or redirect into a mobile-safe handoff URL that can be exchanged for backend credentials

#### `POST /api/auth/refresh`

Purpose:

- mint a fresh access token from a valid refresh token/session

Recommended behavior:

- for web: use an HTTP-only refresh cookie
- for mobile: accept a mobile refresh token in the request body or authorization scheme
- return a fresh access token and expiry metadata

#### `POST /api/auth/logout`

Purpose:

- invalidate standalone auth state
- keep this separate from the old session logout path if needed during migration

Recommended behavior:

- revoke or invalidate the refresh token/session
- clear refresh cookies if present
- make repeated logout safe and idempotent

#### `GET /api/me`

Purpose:

- return current authenticated user for:
  - old session auth
  - dev-only bearer auth
  - future production standalone auth

Recommended direction:

- keep `/api/me` as the stable current-user endpoint across all auth modes

## Token and session strategy

### Access token

Recommended:

- short-lived backend-issued access token
- bearer token for standalone API calls
- target lifetime: about 10 to 15 minutes

Required properties:

- signed by backend
- includes user id and auth mode claims
- no long-lived sensitive session state inside the access token

### Refresh token

Recommended:

- long-lived backend-owned refresh credential
- target lifetime: about 30 days, revocable

Storage:

- web: secure, HTTP-only, same-site cookie
- mobile: OS-backed secure storage

### Expiry and rotation

Recommended:

- access token expires frequently
- refresh token rotates on refresh
- old refresh token becomes invalid after successful rotation when practical

This gives us:

- limited blast radius for access-token leakage
- backend control over logout and revocation
- one auth model for both standalone web and mobile

## Secure storage expectations

### Standalone web

Production recommendation:

- do **not** keep production refresh credentials in local storage
- prefer HTTP-only cookies for refresh state
- keep access token in memory when possible
- if persistence is required, keep it minimal and avoid storing long-lived secrets in script-readable storage

### Mobile

Production recommendation:

- store refresh token in secure OS-backed storage
- keep access token in memory or short-lived local state
- refresh silently when the app resumes or receives a `401`

## Web auth migration path

Recommended path:

1. Keep old `/login` and old Google session auth working.
2. Add `GET /api/auth/google/start` for standalone web.
3. Add `GET /api/auth/google/callback` that finishes backend-owned auth.
4. Add `POST /api/auth/refresh` and keep `GET /api/me` as the stable current-user probe.
5. Update standalone web to stop depending on dev-only login and local-storage bearer-only auth.
6. Verify all protected standalone routes with the production auth path.
7. Only then mark old `/login` as removable.

### Acceptable implementation shapes later

Chosen direction:

- secure HTTP-only refresh cookie for standalone web
- short-lived bearer access token for API calls
- backend refresh endpoint for renewal

That is the safest fit for the browser client while keeping backend ownership intact.

## Mobile auth migration path

Recommended path:

1. Reuse the same backend identity model as standalone web.
2. Support a mobile-friendly Google sign-in entry that still starts with backend-owned Google auth.
3. Exchange the verified identity for backend-issued API credentials.
4. Store refresh credentials in secure mobile storage.
5. Use `POST /api/auth/refresh` for silent renewal.
6. Use `GET /api/me` as the stable authenticated-user check.
7. Use the same protected API surface as standalone web.

The important point is that mobile should not get a separate business logic auth stack. It should share the same backend auth contract.

### Mobile handoff recommendation

For mobile, the most practical next design is:

1. open Google auth in a system browser or in-app browser
2. let backend complete Google callback handling
3. redirect into a mobile-specific callback/handoff URL
4. exchange that handoff for backend access + refresh credentials

That keeps Google secrets and identity verification on the backend.

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

1. add the production auth endpoints listed above
2. implement standalone web first using the cookie + refresh-token design
3. keep dev-only `/api/auth/login` for local development
4. then bring mobile onto the same refresh/access-token contract
