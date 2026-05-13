Continue from current ios branch.

Goal:
Implement production-ready standalone auth for PlantLab web/mobile while keeping old backend-rendered Google/session auth working during transition.

Do not:
- remove old backend-rendered web
- change GCP/deployment
- remove dev-only auth yet
- break mobile/web local development
- refactor unrelated systems

Current state:
- old backend web uses Google/session auth
- standalone web/mobile use dev-only bearer auth
- AUTH_MIGRATION_PLAN.md documents target auth
- backend should remain auth owner

Tasks:

1. Review current auth code and AUTH_MIGRATION_PLAN.md.

2. Implement standalone production auth backend contract:
   - GET /api/auth/google/start
   - GET /api/auth/google/callback
   - POST /api/auth/refresh
   - POST /api/auth/logout
   - GET /api/me

3. Token strategy:
   - short-lived access token
   - refresh credential/session
   - refresh rotation if practical
   - logout invalidates refresh credential
   - standard error envelope

4. Web behavior:
   - standalone web login should use production Google auth when enabled
   - keep dev-login available behind explicit local/dev mode
   - avoid storing long-lived secrets in localStorage
   - use refresh flow to restore session

5. Mobile behavior:
   - prepare mobile auth flow for backend-owned Google auth
   - if full mobile OAuth callback is too much in this pass, add documented implementation path and keep dev auth as fallback
   - use secure storage if already available/practical

6. Keep old auth working:
   - old /auth/login
   - old /auth/callback
   - old /login
   - old session auth
   must remain intact.

7. Update docs:
   - AUTH_MIGRATION_PLAN.md
   - API_CONTRACT_NOTES.md
   - OLD_WEB_RETIREMENT_CHECKLIST.md
   - README auth notes

8. Add tests:
   - refresh success/failure
   - logout idempotency
   - /api/me with production access token
   - dev auth still works in local mode
   - old session auth still works if existing tests cover it

Verification:
- backend tests
- web typecheck
- web build
- mobile typecheck
- Expo iOS export
- old backend-rendered /login still works
- dev local auth still works
- no GCP changes

Autopilot rules:
- staged commits:
  1. backend auth contract
  2. web auth integration
  3. mobile prep/integration
  4. docs/tests
- commit after green verification
- stop if OAuth/client secret/environment setup is missing
- do not fake production auth silently

Report:
1. files changed
2. backend auth endpoints
3. token strategy implemented
4. web auth behavior
5. mobile auth behavior
6. verification results
7. remaining auth gaps