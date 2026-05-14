Feature request: Remove old Render backend references.

Production auth is complete. Clean up the old Render backend so the project uses only the current production backend.

Planner only:
- Search backend, web, mobile, firmware, docs, env examples, scripts, and tests for old Render URLs or Render deployment references.
- Identify what should be removed, replaced, or archived.
- Confirm OAuth redirect/callback URLs no longer reference Render.
- Confirm firmware/backend base URLs point to the current production backend.
- Confirm no secrets are exposed.
- Create a safe cleanup plan only.
- Do not implement yet.

Planner output should include:
1. Current production backend URL usage summary
2. Old Render references found
3. Files likely to change
4. Safe cleanup steps
5. Rollback/backup notes
6. Test plan
7. Risks and assumptions