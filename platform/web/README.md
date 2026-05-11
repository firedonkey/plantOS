# Web

This folder is reserved for the standalone PlantLab browser frontend.

Final intent:

- standalone frontend app
- talks to backend only through API endpoints
- fully replaces backend-rendered web routes in Stage 2

Local dev:

- Copy [`.env.example`](/Users/gary/plantOS/platform/web/.env.example) to `.env` if needed.
- Set `VITE_API_BASE_URL` to your local backend, usually `http://localhost:8000`.
- Start the standalone app with `npm run dev`.
- Keep this app running side-by-side with the backend-rendered web during migration.

Status:

- standalone React/Vite frontend scaffold is in place
- uses backend APIs when available
- keeps mock fallback mode available when the backend is unavailable
- does not replace backend-rendered web routes yet
- manual image capture is intentionally postponed for now
- the standalone UI treats capture as a coming-later capability instead of a broken action

Manual test checklist:

- Backend-rendered web still loads at `http://localhost:8000/devices`
- Standalone web loads at the Vite dev URL
- Dev login works against `POST /api/auth/login`
- Device list loads from the backend when the backend is running
- Dashboard loads summary, readings, and latest image from the backend
- Light and pump commands return success feedback
- Capture command shows the expected friendly unsupported message
- Mock mode still works when `VITE_API_BASE_URL` is missing or the backend is unavailable
