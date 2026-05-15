Feature request: Fix image visibility after GCP deployment.

Problem:
After deploying PlantLab to GCP, uploaded/device images cannot be seen on the mobile app. Web has not been tested yet.

Goal:
Diagnose and fix why images are not visible from the mobile app after GCP deployment.

Use workflow:
Planner → approval → Coder → Tester → Reviewer 

Planner only:
- Study current backend image upload/storage code.
- Study GCP deployment config.
- Study mobile image display code.
- Study env vars for storage/image URL/API base URL.
- Do not implement yet.
- Create a plan only.

Areas to investigate:
1. Backend image storage
- Is production using GCS or local filesystem?
- Is PLANTLAB_STORAGE_BACKEND set correctly?
- Is GCS_BUCKET_NAME set correctly?
- Are uploaded images actually reaching GCS?
- Are image URLs saved correctly in DB?
- Are image URLs absolute or relative?
- Are signed URLs generated if needed?
- Are content types set correctly?

2. GCP permissions
- Does Cloud Run service account have storage.objectAdmin or correct bucket permissions?
- Can Cloud Run write images?
- Can Cloud Run read/generate signed URLs?
- Is bucket public, private with signed URLs, or proxied through backend?

3. Mobile app
- Is mobile API base URL pointing to GCP production backend?
- Is mobile receiving image_url fields from backend?
- Are image URLs valid HTTPS URLs?
- Does React Native Image component support the returned URL format?
- Are auth headers needed for image fetch?
- Are signed URLs expired?
- Are relative URLs incorrectly resolved on mobile?

4. CORS / access behavior
- If web directly loads GCS URLs, check bucket CORS.
- If mobile directly loads GCS URLs, verify URLs are publicly accessible or signed.
- If images are served through backend, verify backend image endpoint works.
- Do not expose private images publicly unless intentional.

5. Debugging commands/checks
Planner should propose safe read-only checks:
- curl backend image API response
- inspect one device image record
- test one image URL in browser
- test one image URL with curl
- check Cloud Run logs for upload/read errors
- check GCS bucket object existence
- check env vars without printing secrets

Expected preferred design:
Planner should recommend one clear production approach:
A. Backend returns short-lived signed image URLs.
B. Backend proxies images through authenticated endpoint.
C. Bucket objects are public-read for MVP only.

Compare tradeoffs and recommend safest/simple approach.

Security requirements:
- Do not commit secrets.
- Do not print tokens.
- Do not make private bucket public unless explicitly approved.
- Signed URLs should not be overly long-lived unless justified.

Tester should verify:
- backend image API returns usable image URL
- mobile can render image from production backend
- missing image does not crash UI
- expired/broken image URL shows fallback UI
- upload path still works
- web image path should be tested if possible
- no secrets in logs

Reviewer should block if:
- production images require local filesystem
- mobile receives relative/broken image URLs
- signed URLs expire too quickly for normal use
- bucket is made public without explicit approval
- CORS/security is handled carelessly
- unrelated auth/provisioning behavior changes

Release Agent should check:
- required GCP env vars
- Cloud Run service account permissions
- GCS bucket name
- image URL strategy
- manual production validation checklist
- rollback plan

Planner output format:
1. Current image storage/display flow summary
2. Production GCP image architecture diagnosis
3. Root cause hypotheses
4. Recommended production image URL strategy
5. Backend changes if needed
6. Mobile changes if needed
7. GCP config/permission changes if needed
8. Read-only debug checklist
9. Implementation steps
10. Test plan
11. Release validation checklist
12. Risks and assumptions
