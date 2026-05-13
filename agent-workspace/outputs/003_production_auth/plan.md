# 1. Summary

Implement standalone production auth as an additive backend-owned contract while preserving the existing backend-rendered Google/session flow and local dev bearer auth.

Primary direction:

- Keep old `/auth/login`, `/auth/callback`, `/auth/logout`, and `/login` intact.
- Add standalone `/api/auth/google/start`, `/api/auth/google/callback`, `/api/auth/refresh`, `/api/auth/logout`, and production bearer support for `/api/me`.
- Use short-lived backend-signed access tokens plus revocable refresh sessions.
- Web uses Google OAuth + HTTP-only refresh cookie; access token stays in memory.
- Mobile is prepared for backend-owned Google auth, but remains dev-auth fallback unless secure refresh storage is available.

# 2. Scope

In scope:

- Backend standalone auth routes, token/session service, DB model, migration, schemas, and tests.
- Web auth integration for production Google flow and explicit local dev-login mode.
- Mobile auth API/session prep and documented fallback if secure storage/deep-link handoff cannot be completed safely.
- Auth docs and README notes.
- Verification commands listed in the task.

Out of scope:

- Removing backend-rendered web.
- GCP/deployment changes.
- Removing `POST /api/auth/login`.
- Refactoring unrelated API, device, provisioning, image, or UI systems.
- Silently faking production OAuth when Google env/setup is missing.

# 3. Proposed Design

Backend remains the auth owner.

Add a production standalone auth service:

- Access token:
  - signed with `APP_SECRET_KEY` using `itsdangerous` under a new production salt
  - payload includes `user_id`, `mode="standalone"`, and token metadata
  - validated with max age, default 15 minutes
  - returned as bearer token to standalone clients
- Refresh credential:
  - generated with `secrets.token_urlsafe`
  - only a SHA-256 hash is stored server-side
  - default lifetime 30 days
  - rotated on every successful refresh
  - revoked on logout
- Mobile handoff, if implemented:
  - use short-lived one-time handoff codes stored hashed server-side
  - do not put refresh tokens directly in deep links
  - `POST /api/auth/refresh` may accept either a refresh cookie, `{ "refresh_token": "..." }`, or `{ "handoff_code": "..." }`

Backend endpoint behavior:

- `GET /api/auth/google/start`
  - requires Google OAuth config; otherwise returns standard API error `503 google_auth_not_configured`
  - accepts `client=web|mobile` and optional `return_to`
  - validates `return_to` against relative paths, configured standalone web origin regex, or the mobile scheme if supported
  - starts Google OAuth with standalone callback URL
- `GET /api/auth/google/callback`
  - completes Google OAuth
  - upserts user via existing `upsert_google_user`
  - does not alter old `/auth/callback`
  - for web:
    - creates refresh session
    - sets secure HTTP-only refresh cookie
    - also sets `request.session["user_id"]` during transition so existing protected image/content routes still work in browser contexts
    - redirects back to standalone web, where the app calls refresh
  - for mobile:
    - if full handoff is implemented, creates a one-time handoff code and redirects to `plantlab://...`
    - if not implemented, redirects with an explicit error and docs must state mobile production auth is not enabled yet
- `POST /api/auth/refresh`
  - web: reads refresh cookie
  - mobile: reads refresh token or handoff code from JSON body
  - rotates refresh sessions when practical
  - returns access token, expiry metadata, user, and mobile refresh token only when needed
  - returns standard error envelope on missing/invalid/expired refresh
- `POST /api/auth/logout`
  - accepts cookie and optional body refresh token
  - revokes matching refresh session if present
  - clears refresh cookie
  - idempotent success even if already logged out
- `GET /api/me`
  - keeps current response shape
  - accepts old session auth, dev bearer auth when enabled, and production standalone bearer auth

Data model:

- Add `AuthRefreshSession` with user FK, token hash, expiry, created/used/revoked timestamps, and replacement reference.
- Add `AuthHandoffCode` only if mobile handoff is implemented in this pass.
- Add Alembic migration for new tables and indexes.

Web behavior:

- Add explicit auth config, for example `VITE_AUTH_MODE=production|dev` or `VITE_ENABLE_DEV_AUTH=true`.
- Local `.env.example` may keep dev auth explicit so local development does not break.
- Production login screen shows Google sign-in using `/api/auth/google/start`.
- Dev login form is shown only in explicit dev mode.
- Production refresh cookie is HTTP-only; access token is kept in React state only.
- On app load, call `/api/auth/refresh` with `credentials: "include"` to restore session.
- On sign-out, call `/api/auth/logout`, then clear in-memory session and any dev localStorage session.

Mobile behavior:

- Add API functions for production refresh/logout and backend Google start URL.
- Keep dev auth as default fallback unless production mobile auth can store refresh credentials securely.
- Since `expo-secure-store` is not currently installed, do not store production refresh tokens in AsyncStorage unless the Coder can safely add and verify `expo-secure-store`.
- If secure storage or deep-link handoff is not completed, document the exact backend handoff path and leave mobile dev login clearly marked local/dev only.

# 4. Files Likely To Change

Backend:

- `platform/backend/app/core/settings.py`
- `platform/backend/app/api/deps.py`
- `platform/backend/app/api/routes/auth.py`
- `platform/backend/app/schemas/auth.py`
- `platform/backend/app/models/__init__.py`
- `platform/backend/app/models/auth.py` or similar new model file
- `platform/backend/app/services/standalone_auth.py` new service
- `platform/backend/migrations/versions/<new>_standalone_auth_sessions.py`
- `platform/backend/tests/test_auth.py`
- optionally `platform/backend/tests/test_standalone_auth.py`

Web:

- `platform/web/src/api/auth.ts`
- `platform/web/src/api/client.ts`
- `platform/web/src/api/config.ts`
- `platform/web/src/hooks/useSession.tsx`
- `platform/web/src/screens/LoginScreen.tsx`
- `platform/web/src/screens/SettingsScreen.tsx`
- `platform/web/src/screens/LandingScreen.tsx`
- `platform/web/src/types/index.ts`
- `platform/web/.env.example`
- `platform/web/README.md`

Mobile:

- `platform/mobile/src/api/auth.ts`
- `platform/mobile/src/api/client.ts`
- `platform/mobile/src/api/config.ts`
- `platform/mobile/src/hooks/useSession.tsx`
- `platform/mobile/src/storage/auth.ts`
- `platform/mobile/src/screens/LoginScreen.tsx`
- `platform/mobile/src/screens/SettingsScreen.tsx`
- `platform/mobile/src/types/index.ts`
- `platform/mobile/.env.example`
- `platform/mobile/README.md`
- `platform/mobile/package.json` and lockfile only if adding verified secure-storage/browser dependency

Docs:

- `platform/shared/docs/AUTH_MIGRATION_PLAN.md`
- `platform/shared/docs/API_CONTRACT_NOTES.md`
- `platform/shared/docs/OLD_WEB_RETIREMENT_CHECKLIST.md`
- `README.md`
- optionally `platform/backend/README.md`

# 5. Implementation Steps

1. Backend auth contract commit:
   - Add settings for access TTL, refresh TTL, refresh cookie name, cookie same-site, and optional mobile deep-link scheme.
   - Add auth refresh session model and migration.
   - Add standalone auth service helpers:
     - issue/validate access token
     - create refresh session
     - consume/rotate refresh session
     - revoke refresh session
     - optional handoff code create/consume
   - Update `get_optional_current_user` to try production bearer token before dev bearer token.
   - Add the new `/api/auth/*` routes without changing old `/auth/*` routes.
   - Keep `/api/me` response stable.

2. Web auth integration commit:
   - Add production auth config helpers.
   - Update `apiRequest` to support `credentials: "include"` and keep bearer header support.
   - Add refresh/logout/start helpers.
   - Update `SessionProvider`:
     - restore production session through refresh on mount
     - store production access token only in memory
     - keep dev session localStorage only when dev auth is explicitly enabled
   - Update login/settings/landing copy to reflect production Google auth plus explicit dev mode.

3. Mobile prep/integration commit:
   - Add production auth API helper functions.
   - Extend session types for `dev`, `production`, and `mock`.
   - If secure storage can be added and verified, store mobile refresh token there and wire handoff callback.
   - If not, keep dev login active and add an explicit production-auth unavailable path with docs. Do not store production refresh tokens in AsyncStorage.

4. Docs/tests commit:
   - Update migration/API/checklist docs to mark backend contract implemented and mobile status accurately.
   - Update README auth notes and local env examples.
   - Add backend tests for refresh, logout, `/api/me`, dev auth, and old session behavior.
   - Run verification before committing each stage if the orchestrator permits commits.

# 6. Test And Verification Plan

Backend automated tests:

- `POST /api/auth/refresh` succeeds with valid web cookie and returns a production access token.
- Refresh rotates token; old refresh credential fails afterward.
- Expired/revoked/missing refresh returns standard error envelope.
- `POST /api/auth/logout` succeeds repeatedly and revokes refresh credential.
- `GET /api/me` authenticates with production access token.
- Existing dev login still works when `PLANTLAB_DEV_TOKEN_AUTH_ENABLED=true`.
- Dev login still returns `403 dev_token_auth_disabled` when disabled.
- Old session auth remains valid via a focused `get_optional_current_user` test using a request session.
- Old `/auth/login` missing-config behavior remains unchanged.
- Mock Google callback by monkeypatching Authlib instead of calling Google.

Commands:

- `cd platform/backend && python -m pytest tests`
- `cd platform/web && npm run typecheck`
- `cd platform/web && npm run build`
- `cd platform/mobile && npm run typecheck`
- `cd platform/mobile && npx expo export --platform ios`

Manual/local checks:

- Old backend-rendered `/login` still loads.
- Old `/auth/login`, `/auth/callback`, `/auth/logout` route names remain present.
- Standalone web dev auth works only when explicit dev mode is enabled.
- Standalone web production login does not proceed if Google OAuth env is missing; it shows/reports explicit configuration failure.
- No GCP/deployment files are changed.

# 7. Risks And Open Questions

- The current worktree is dirty on branch `ios`; Coder must not revert unrelated agent-workspace or device changes.
- Live Google OAuth cannot be fully verified without real `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`; tests should mock callback behavior and manual E2E should stop if env is missing.
- Mobile secure storage is not currently installed. If adding `expo-secure-store` is not practical and verified, mobile production refresh-token persistence must remain a documented gap.
- Cross-site production web deployments may need stricter origin/CSRF policy before using `SameSite=None`; default should remain secure, conservative cookie settings.
- Browser image/content routes may still rely on old session cookies during transition; setting the backend session in the standalone callback is an intentional compatibility bridge, not the final auth model.

# 8. Explicit Approval Checklist

- [ ] Approve adding backend DB tables for standalone refresh sessions and optional mobile handoff codes.
- [ ] Approve using `APP_SECRET_KEY`/itsdangerous for signed short-lived access tokens in this pass.
- [ ] Approve refresh-token rotation and logout revocation semantics.
- [ ] Approve web production auth using HTTP-only refresh cookie plus in-memory access token.
- [ ] Approve keeping dev bearer login available only behind explicit local/dev config.
- [ ] Approve mobile production auth being documented as incomplete if secure storage/deep-link handoff cannot be safely verified.
- [ ] Confirm no GCP/deployment changes should be made.
- [ ] Confirm old backend-rendered Google/session auth must remain untouched except for additive shared helpers.