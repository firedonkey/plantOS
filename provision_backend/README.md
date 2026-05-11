# PlantLab Provision Backend

This module implements the onboarding APIs described in [SoftAP Provisioning Design](/Users/gary/plantOS/docs/design/softap_provisioning_design.md).

## File Structure

```text
provision_backend/
  package.json
  README.md
  src/
    app.js
    config.js
    db/
      pool.js
      provisioning_schema.sql
    frontend/
      components/
        AddDevicePage.jsx
      lib/
        deviceClaimApi.js
      styles/
        add-device.css
    lib/
      errors.js
      tokens.js
    middleware/
      devAuth.js
      requireAuthenticatedUser.js
    models/
      provisioningSchemas.js
    routes/
      devices.js
    services/
      deviceProvisioningService.js
```

## API Summary

### `POST /api/devices/claim-token`

- Requires an authenticated user on `req.user`
- Creates a short-lived, one-time-use claim token

Example success response:

```json
{
  "ok": true,
  "claim_token": "PL-ABC123XYZ",
  "expires_at": "2026-04-20T00:30:00.000Z"
}
```

Example unauthorized response:

```json
{
  "ok": false,
  "error": "unauthorized",
  "message": "You must be signed in to perform this action.",
  "details": null
}
```

### `POST /api/devices/register`

Accepts:

```json
{
  "device_id": "pl-device-0001",
  "claim_token": "PL-ABC123XYZ",
  "hardware_version": "rev_a",
  "software_version": "0.1.0",
  "capabilities": {
    "camera": true,
    "pump": true,
    "moisture_sensor": true,
    "light_control": true
  }
}
```

Example success response:

```json
{
  "ok": true,
  "device_id": "pl-device-0001",
  "device_name": "PlantLab pl-device-0001",
  "status": "online",
  "device_access_token": "pla_hJ2v4nYI6b4U..."
}
```

Example invalid token response:

```json
{
  "ok": false,
  "error": "invalid_or_expired_claim_token",
  "message": "Claim token has expired.",
  "details": null
}
```

## Notes for Integrating with an Existing Auth System

1. Replace the stub middleware in `src/app.js` with your real auth middleware.
2. Make sure authenticated requests populate:

   ```js
   req.user = { id: 123, email: "user@example.com" };
   ```

3. Keep `POST /api/devices/register` unauthenticated. The device proves ownership through the claim token.
4. Keep claim tokens short-lived. The current default is 15 minutes.
5. Store only a hash of the long-term device token in the database.
6. Consider revoking older device tokens if you want only one active token per device.
7. Add rate limiting in front of both endpoints in production.

## Suggested Startup

```bash
cd provision_backend
npm install
DATABASE_URL=postgresql://user:password@localhost:5432/plantlab npm run dev
```

Local dev auth for claim-token testing:

```bash
ENABLE_DEV_AUTH=true \
DEV_AUTH_USER_ID=1 \
DATABASE_URL=postgresql://user:password@localhost:5432/plantlab \
npm run dev
```

## Website Add Device Page

The React Add Device page lives in:

- `src/frontend/components/AddDevicePage.jsx`
- `src/frontend/lib/deviceClaimApi.js`
- `src/frontend/styles/add-device.css`

It assumes the user is already logged in and that the backend session cookie is available to the browser. The page calls:

```http
POST /api/devices/claim-token
```

with:

```js
credentials: "include"
```

so it can work with cookie/session auth.

Example integration:

```jsx
import AddDevicePage from "./components/AddDevicePage.jsx";

export default function App() {
  return <AddDevicePage />;
}
```

If your frontend and backend run on different domains, enable CORS for the frontend origin and allow credentials on the backend.
