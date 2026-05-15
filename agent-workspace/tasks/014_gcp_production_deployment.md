Feature request: Deploy PlantLab backend to Google Cloud Platform production.

Context:
PlantLab local build is about 80% feature-complete. BLE provisioning works. Production auth is done. Now prepare and deploy the backend to GCP safely.

Goal:
Deploy the PlantLab backend to GCP production with a safe, repeatable process.

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current backend deployment setup.
- Study Dockerfile, env vars, database config, auth config, storage config, migrations, and docs.
- Do not deploy yet.
- Do not change production infra yet.
- Create a deployment plan only.

Target GCP services:
- Cloud Run for backend API
- Cloud SQL PostgreSQL
- Secret Manager
- Cloud Storage for uploaded images
- Artifact Registry for Docker image
- Custom domain if already configured

Planner should verify:
1. Current backend entrypoint and Dockerfile
2. Required environment variables
3. Required secrets
4. Cloud SQL connection config
5. GCS bucket config
6. OAuth redirect URLs
7. Device token / hardware API behavior
8. Database migration process
9. CORS config for web/mobile
10. Health check endpoint
11. Rollback strategy

Deployment must be staged:
1. Preflight check
2. Build Docker image
3. Push to Artifact Registry
4. Deploy to Cloud Run staging or production
5. Run database migrations
6. Verify health check
7. Verify auth
8. Verify device heartbeat/readings
9. Verify image upload
10. Verify mobile app API connection

Security requirements:
- Do not commit secrets.
- Use Secret Manager.
- Do not print secrets in logs.
- Confirm service account permissions are minimal.
- Confirm production CORS is not wide open unless intentionally temporary.

Release Agent:
- Must be read-only.
- Must not deploy automatically.
- Must create release_report.md with deployment checklist, risks, and manual approval steps.

Planner output format:
1. Current deployment readiness summary
2. GCP architecture
3. Required GCP resources
4. Required secrets/env vars
5. Database migration plan
6. Storage/image upload plan
7. Auth/OAuth configuration plan
8. Device API verification plan
9. Deployment commands
10. Rollback plan
11. Test plan
12. Release checklist
13. Risks and assumptions

Stop after writing the plan.
Do not deploy until I approve.