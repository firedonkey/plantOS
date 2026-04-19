# PlantLab Deployment Guide for Google Cloud

This guide shows how to take a PlantLab service that already works locally, containerize it with Docker, and deploy it to **Google Cloud Run** using **Cloud SQL (PostgreSQL)** and **Cloud Storage**.

It is written to be **Codex-friendly** so you can paste sections into Codex and ask it to update your codebase.

---

## 1. Target architecture

Use this architecture for PlantLab v1:

- **Cloud Run**: run the backend API
- **Cloud SQL for PostgreSQL**: users, devices, tokens, sensor data, metadata
- **Cloud Storage**: plant images and uploaded files
- **Artifact Registry**: store Docker images
- **Secret Manager**: store secrets safely

Flow:

1. Device sends sensor data and image requests to backend API
2. Backend stores structured data in PostgreSQL
3. Backend uploads image files to Cloud Storage
4. Web dashboard calls backend API

---

## 2. What you should change in the app before deployment

Before deploying, the app should follow these rules:

### 2.1 Move all config into environment variables

Do **not** hardcode:

- database host
- database username/password
- secret keys
- bucket names
- API base URLs
- debug flags

Typical environment variables:

```env
PORT=8080
APP_ENV=production
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
PLANTLAB_SESSION_SECRET=replace_me
GCS_BUCKET_NAME=plantlab-images
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
```

### 2.2 Do not store permanent images on local disk

On Cloud Run, the container filesystem is not your permanent storage.

Rules:

- okay: temporary files in `/tmp`
- not okay: saving user images permanently inside the container

Plant images should be uploaded to **Google Cloud Storage**.

### 2.3 Make sure the app listens on `0.0.0.0:$PORT`

Cloud Run sends traffic to the port in the `PORT` environment variable, usually `8080`.

Examples:

#### FastAPI / Uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

#### Flask

```python
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

#### Node / Express

```javascript
const port = process.env.PORT || 8080;
app.listen(port, '0.0.0.0', () => {
  console.log(`Listening on ${port}`);
});
```

### 2.4 Add a health endpoint

Create something like:

- `GET /health`

Example response:

```json
{"status": "ok"}
```

### 2.5 Prepare database migrations

If you use migrations, make sure they can run in production.

Examples:

- Alembic for FastAPI / SQLAlchemy
- Prisma / Knex / Sequelize migrations for Node
- Django migrations

PlantLab uses Alembic for the platform database schema. Before the first
production deploy, and after each schema change, run this from the
`platform/` directory with the same database environment variables Cloud Run
will use:

```bash
alembic upgrade head
```

---

## 3. Ask Codex to prepare the app for Google Cloud

You can give Codex prompts like these.

### Prompt 1: production config cleanup

```text
Please update this codebase for Google Cloud deployment.

Requirements:
- Move all config to environment variables
- App must listen on 0.0.0.0 and process.env.PORT or PORT env var
- Add GET /health endpoint returning {"status":"ok"}
- Replace any permanent local file storage with a storage abstraction so images can be saved to Google Cloud Storage later
- Keep local development working with a .env file
- Create or update .env.example
- Explain every code change you make
```

### Prompt 2: Cloud Storage integration

```text
Please add Google Cloud Storage support to this codebase.

Requirements:
- Use bucket name from GCS_BUCKET_NAME env var
- Upload plant images to Cloud Storage instead of saving permanently on local disk
- Return stored object path or public URL as metadata
- Use /tmp only for temporary processing if needed
- Keep code modular so local storage can still be used in development
- Show me which files you changed and why
```

### Prompt 3: Docker preparation

```text
Please create a production-ready Docker setup for this application.

Requirements:
- Add Dockerfile
- Add .dockerignore
- Use a minimal base image
- Install dependencies correctly
- Expose port 8080
- Run the app with a production command
- Keep image size reasonable
- Explain how to build and run it locally
```

---

## 4. How to build a Dockerfile

The exact Dockerfile depends on your backend stack, but the structure is similar.

### 4.1 General Dockerfile pattern

A Dockerfile usually does this:

1. choose a base image
2. set working directory
3. copy dependency files first
4. install dependencies
5. copy the rest of the code
6. set environment variables if needed
7. expose port
8. start the server

---

## 5. Example Dockerfiles

Pick the one closest to your backend.

---

### 5.1 Example Dockerfile for Python FastAPI

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

If you use `pyproject.toml` instead of `requirements.txt`, ask Codex to adapt it.

---

### 5.2 Example Dockerfile for Flask

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT} app:app"]
```

Replace `app:app` with your actual Flask entrypoint.

---

### 5.3 Example Dockerfile for Node / Express

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["npm", "start"]
```

If your app needs a build step:

```dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist ./dist
ENV PORT=8080
EXPOSE 8080
CMD ["node", "dist/index.js"]
```

---

## 6. Create a `.dockerignore`

This keeps the image smaller and cleaner.

Example:

```dockerignore
.git
.gitignore
node_modules
venv
.venv
__pycache__
*.pyc
.env
.env.*
Dockerfile*
README.md
tests
.cache
.dist
build
```

You may need to adjust this for your project.

---

## 7. Test Docker locally before using Google Cloud

Build the image:

```bash
docker build -t plantlab-backend .
```

Run the image locally:

```bash
docker run --rm -p 8080:8080 \
  -e PORT=8080 \
  -e APP_ENV=production \
  -e DATABASE_URL="your_local_or_test_db_url" \
  -e PLANTLAB_SESSION_SECRET="test-secret" \
  -e GCS_BUCKET_NAME="dummy-bucket" \
  plantlab-backend
```

Then test:

```bash
curl http://localhost:8080/health
```

Expected result:

```json
{"status":"ok"}
```

If this does not work locally in Docker, do not deploy yet.

---

## 8. Set up Google Cloud

### 8.1 Create a Google Cloud project

In the Google Cloud Console:

1. Create a new project
2. Enable billing
3. Note the **Project ID**

For the current PlantLab Google Cloud project, use:

```bash
PROJECT_ID=plantlab-493805
REGION=us-central1
SERVICE_NAME=plantlab-api
DB_INSTANCE=plantlab
DB_NAME=plantlab
DB_USER=plantlab_user
BUCKET_NAME=plantlab-images-garylu
CLOUD_SQL_CONNECTION_NAME=plantlab-493805:us-central1:plantlab
```

Pick a region close to your users. If you are in California, `us-west1` or `us-west2` may make sense, but `us-central1` is often commonly used.

---

### 8.2 Install Google Cloud CLI

Install and initialize the CLI:

```bash
gcloud init
```

Set your project:

```bash
gcloud config set project $PROJECT_ID
```

---

### 8.3 Enable required APIs

```bash
gcloud services enable run.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com
```

---

## 9. Create Artifact Registry for Docker images

```bash
gcloud artifacts repositories create plantlab-repo \
  --repository-format=docker \
  --location=$REGION \
  --description="PlantLab Docker repository"
```

Configure Docker auth:

```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

---

## 10. Create a Cloud Storage bucket

```bash
gsutil mb -l $REGION gs://$BUCKET_NAME
```

This bucket will store plant images.

---

## 11. Create PostgreSQL in Cloud SQL

### 11.1 Create instance

```bash
gcloud sql instances create $DB_INSTANCE \
  --database-version=POSTGRES_15 \
  --cpu=1 \
  --memory=3840MiB \
  --region=$REGION
```

This is just a starting size. You can tune later.

### 11.2 Create database

```bash
gcloud sql databases create $DB_NAME --instance=$DB_INSTANCE
```

### 11.3 Create user

```bash
gcloud sql users create $DB_USER \
  --instance=$DB_INSTANCE \
  --password='CHANGE_ME_NOW'
```

---

## 12. Store secrets in Secret Manager

### 12.1 Database password

```bash
echo -n 'CHANGE_ME_NOW' | gcloud secrets create db-password --data-file=-
```

### 12.2 App secret key

```bash
echo -n 'replace-with-a-strong-secret-key' | gcloud secrets create app-secret-key --data-file=-
```

If the secret already exists later, use:

```bash
echo -n 'new-value' | gcloud secrets versions add db-password --data-file=-
```

---

## 13. Build and push your Docker image

Set image name:

```bash
IMAGE_URI=${REGION}-docker.pkg.dev/${PROJECT_ID}/plantlab-repo/plantlab-api:latest
```

Build and push with Cloud Build:

```bash
gcloud builds submit --tag $IMAGE_URI
```

This uploads your code, builds the Docker image, and pushes it to Artifact Registry.

---

## 14. Deploy to Cloud Run

First get the Cloud SQL connection name:

```bash
CLOUD_SQL_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE --format='value(connectionName)')
echo $CLOUD_SQL_CONNECTION_NAME
```

Deploy:

```bash
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_URI \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars APP_ENV=production,PLANTLAB_STORAGE_BACKEND=gcs,GCS_BUCKET_NAME=$BUCKET_NAME,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,DB_NAME=$DB_NAME,DB_USER=$DB_USER,CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_CONNECTION_NAME \
  --set-secrets PLANTLAB_SESSION_SECRET=app-secret-key:latest,DB_PASSWORD=db-password:latest \
  --add-cloudsql-instances $CLOUD_SQL_CONNECTION_NAME
```

### Important note about database connection strings

For Cloud SQL, many apps connect using one of these approaches:

1. **Cloud SQL connector / Unix socket approach**
2. **Private IP / direct host approach**

For Cloud Run, the Unix socket approach is very common.

Example host for PostgreSQL Unix socket:

```text
/CloudSQL/PROJECT:REGION:INSTANCE
```

Or more commonly in code:

```text
/CloudSQL/<connection_name>
```

Ask Codex to configure your framework correctly for **Cloud Run + Cloud SQL Postgres via Unix socket**.

Example prompt:

```text
Please update this application to connect to PostgreSQL on Google Cloud SQL from Cloud Run.

Requirements:
- Support DATABASE_URL for local development
- In production, support Cloud SQL Unix socket connection using Cloud Run
- Read DB name, user, password, and Cloud SQL connection name from environment variables or secrets
- Keep the code clean and production-safe
- Explain exactly which connection settings you changed
```

---

## 15. Give Cloud Run access to Cloud Storage and secrets

Find the Cloud Run service account. By default it may use the Compute Engine default service account unless you set a custom one.

You can create a dedicated service account, which is cleaner.

### 15.1 Create service account

```bash
gcloud iam service-accounts create plantlab-run-sa \
  --display-name="PlantLab Cloud Run Service Account"
```

### 15.2 Grant storage access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:plantlab-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### 15.3 Grant secret access

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:plantlab-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 15.4 Update Cloud Run to use that service account

```bash
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --service-account=plantlab-run-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

---

## 16. Recommended production environment variables

A good production setup might use these:

```env
APP_ENV=production
PORT=8080
GOOGLE_CLOUD_PROJECT=plantlab-493805
PLANTLAB_STORAGE_BACKEND=gcs
GCS_BUCKET_NAME=plantlab-images-garylu
DB_NAME=plantlab
DB_USER=plantlab_user
DB_PASSWORD=from-secret-manager
CLOUD_SQL_CONNECTION_NAME=plantlab-493805:us-central1:plantlab
PLANTLAB_SESSION_SECRET=from-secret-manager
```

If your code prefers a single `DATABASE_URL`, ask Codex to build it from components in production.

---

## 17. Run database migrations

You have a few choices.

### Option A: run migrations from your laptop

For example:

```bash
export DATABASE_URL='your_cloud_sql_connection_string'
alembic upgrade head
```

### Option B: run migrations in a one-off Docker command

### Option C: build migration into deploy workflow

For v1, the simplest safe option is often:

- deploy app
- run migration manually
- verify app works

Ask Codex to recommend the cleanest migration flow for your framework.

Prompt:

```text
Please inspect this codebase and tell me the safest way to run database migrations for Google Cloud deployment.

Requirements:
- Keep local development working
- Production DB is PostgreSQL on Cloud SQL
- I want a repeatable migration process
- Show me exact commands and any files that need to change
```

---

## 18. Verify the deployment

Get service URL:

```bash
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format='value(status.url)'
```

Test health endpoint:

```bash
curl https://YOUR_CLOUD_RUN_URL/health
```

Check logs:

```bash
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" --limit=50
```

---

## 19. Redeploy after code changes

Each time you update the app:

```bash
IMAGE_URI=${REGION}-docker.pkg.dev/${PROJECT_ID}/plantlab-repo/plantlab-api:latest
gcloud builds submit --tag $IMAGE_URI

gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_URI \
  --region $REGION \
  --platform managed
```

---

## 20. Optional: use a custom domain

After the service is stable, you can map a custom domain in Cloud Run.

High-level flow:

1. verify domain ownership
2. map domain to Cloud Run service
3. update DNS records

Do this after your API is already working.

---

## 21. Suggested first production milestone for PlantLab

Do not try to deploy everything at once.

### Milestone 1

Deploy only this:

- `POST /api/device-data`
- `GET /health`
- PostgreSQL connection
- image upload to Cloud Storage

This proves your full cloud path works.

### Milestone 2

Add:

- authentication
- dashboard views
- device registration tokens
- image browsing/history

### Milestone 3

Add:

- background jobs
- alerts
- analytics
- reports

---

## 22. Common mistakes to avoid

### Mistake 1: using local filesystem as permanent storage
Use Cloud Storage instead.

### Mistake 2: forgetting to listen on `0.0.0.0:$PORT`
Cloud Run will fail to route traffic correctly.

### Mistake 3: hardcoding secrets
Use Secret Manager or environment variables.

### Mistake 4: deploying before Docker works locally
Always test locally first.

### Mistake 5: mixing local SQLite assumptions with PostgreSQL
Cloud SQL uses PostgreSQL behavior. Some local DB assumptions may break.

### Mistake 6: no health endpoint
Make troubleshooting harder than it needs to be.

---

## 23. Good Codex workflow for this project

Use Codex in this order.

### Step 1

```text
Please inspect this repository and identify:
- backend framework
- app entrypoint
- dependency files
- where config is currently loaded
- where images/files are currently stored
- what must change for Docker + Google Cloud Run deployment

Give me a short deployment readiness report before changing code.
```

### Step 2

```text
Now make the minimum code changes needed so the app can run on Google Cloud Run.

Requirements:
- production env vars
- health endpoint
- listen on 0.0.0.0:$PORT
- Dockerfile
- .dockerignore
- no permanent local file storage
- keep local development working

After changes, list every modified file and why.
```

### Step 3

```text
Now add Google Cloud Storage integration for uploaded plant images.
Use GCS_BUCKET_NAME from env vars.
Keep the code modular and explain how local dev should work.
```

### Step 4

```text
Now help me prepare Cloud SQL PostgreSQL support for production.
Support local DATABASE_URL for development, and a production-safe config for Cloud Run.
Explain the migration steps and exact environment variables required.
```

---

## 24. Final checklist before production

Before you call the deployment done, verify all of these:

- [ ] app runs locally without Docker
- [ ] app runs locally with Docker
- [ ] `/health` works
- [ ] production env vars documented in `.env.example`
- [ ] secrets are not committed to git
- [ ] images upload to Cloud Storage
- [ ] database writes to PostgreSQL
- [ ] Cloud Run service responds successfully
- [ ] logs are readable
- [ ] first real device can send test data successfully

---

## 25. Minimum files your repo should probably have

```text
Dockerfile
.dockerignore
.env.example
README.md
app/... or src/...
requirements.txt or package.json
```

Potentially also:

```text
alembic.ini
migrations/
cloudbuild.yaml
```

---

## 26. If you want Codex to write the Dockerfile from scratch

Paste this:

```text
Please inspect this repository and create a production-ready Dockerfile for Google Cloud Run.

Requirements:
- Use the correct runtime for this codebase
- App must listen on 0.0.0.0 and PORT env var
- Include only production dependencies
- Keep image size reasonable
- Add .dockerignore
- Show me the exact docker build and docker run commands
- Explain any assumptions about the app entrypoint
```

---

## 27. If you want Codex to review deployment blockers

Paste this:

```text
Please act as a deployment reviewer for this repository.
I want to deploy it to Google Cloud Run with Cloud SQL Postgres and Cloud Storage.

Please find:
- anything that will break in Docker
- anything that assumes local filesystem persistence
- anything that assumes SQLite or local DB
- any missing health endpoint
- any hardcoded secrets or config
- any missing production environment variables

Then propose the smallest safe set of changes.
```

---

## 28. Practical recommendation

Do not aim for perfect architecture in the first deployment.

Your first goal is simply:

- backend reachable on Cloud Run
- database connected
- one test image stored in Cloud Storage
- one test sensor payload saved in PostgreSQL

Once that works, the rest becomes much easier.

---

## 29. Notes for later improvements

Later, you may want to add:

- separate frontend hosting
- background task queue
- signed URLs for secure image access
- custom domain
- CI/CD from GitHub
- separate staging and production environments
- Terraform or infrastructure-as-code

But for now, do **not** overbuild.

---

## 30. What to do right now

1. give this file to Codex
2. ask Codex to inspect your repo and identify the backend stack
3. let Codex update the code for env vars, health endpoint, Dockerfile, and storage abstraction
4. test Docker locally
5. create Google Cloud resources
6. deploy to Cloud Run

That is the right next move.
