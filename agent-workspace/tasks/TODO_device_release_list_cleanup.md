# TODO: Device Release List Cleanup

## Background

The mobile `Prepare device for transfer` and physical factory-reset flow is not fully aligned with the active device list.

Observed behavior:

- User taps `Prepare device for transfer` in mobile device settings.
- User physically holds the ESP32 button for 15 seconds.
- ESP32 clears local credentials and reboots into BLE provisioning mode.
- The device still appears in the mobile Devices list.
- After a few minutes, the device status changes to stale instead of disappearing immediately.

Recent ESP32 logs confirm that the physical reset path clears local credentials:

```text
[button] factory reset hold detected -> clearing credentials
[provisioning] clearing config from Preferences
[provisioning] credentials cleared, reboot scheduled
[provisioning] rebooting ESP32 reason=factory_reset
```

The log does not prove that the mobile app successfully called the backend release endpoint. Physical reset alone cannot remove the backend record from the user account unless the backend release/factory-reset endpoint is called successfully before credentials are cleared.

## Current Status

Known backend behavior:

- Backend has release/archive support.
- Released devices should be excluded from the active list via `released_at IS NULL` and `archived_at IS NULL`.
- Backend tests currently cover release behavior.

Known mobile behavior:

- Mobile has a `Prepare device for transfer` action.
- Mobile attempts to hide released/removed devices locally after successful release.
- The real-device test still showed the device in the list, so the end-to-end release/list path is not yet reliable.

Known firmware behavior:

- 15-second button hold clears local ESP32 credentials.
- This local reset is separate from backend ownership release.
- Firmware does not currently provide clear user-facing confirmation that backend release happened, only that local credentials were cleared.

## Problem To Fix

Make the transfer/release flow deterministic:

1. When mobile user confirms `Prepare device for transfer`, the backend release endpoint must be called and verified.
2. After backend release succeeds, the device must disappear from the active device list immediately.
3. If backend release fails, mobile must not instruct the user to factory reset yet.
4. If the user only performs physical factory reset, the app should explain that backend ownership is unchanged unless release was completed first.
5. Avoid relying on stale heartbeat/offline detection as the signal that a device was removed.

## Investigation Checklist

- Confirm mobile is calling `POST /api/devices/{id}/release` with the correct auth token.
- Confirm backend returns 200 and includes `status=released`.
- Confirm backend writes `released_at`, `archived_at`, and `release_reason=owner_transfer`.
- Confirm `GET /api/devices` excludes the released device for the same user/session.
- Confirm mobile is not using a stale local cache or a different auth/session mode.
- Confirm local dev mode and production mode behave the same.
- Confirm deleted/released devices do not reappear after app reload, pull-to-refresh, or auto-refresh.

## Candidate Fix

- Make mobile release flow backend-first:
  - Call release endpoint.
  - Refetch active devices immediately.
  - Navigate back only after refetch confirms the device is absent.
  - Show explicit success text: “Device released from this account. Now hold the device button for 15 seconds.”

- Improve failure handling:
  - If release API fails, show the exact backend error.
  - Do not show the 15-second factory reset instruction as a completed step.

- Add optional backend/mobile diagnostics:
  - Log release endpoint status in dev builds.
  - Add a local status script check for a device ID’s `released_at` / `archived_at`.

- Consider firmware/backend follow-up:
  - If device still has a valid device token during 15-second factory reset, firmware could call `/api/devices/{id}/factory-reset` before clearing credentials.
  - This should be best-effort only and should not replace the mobile transfer flow.

## Acceptance Criteria

- After `Prepare device for transfer` succeeds, the device disappears from the mobile active list immediately.
- Pull-to-refresh does not bring the released device back.
- App restart does not bring the released device back.
- Backend database row has `released_at` and `archived_at` populated.
- Physical factory reset still clears local credentials after the user completes backend release.
- If backend release fails, the device remains visible and the UI tells the user release did not complete.

## Verification

- Backend release tests pass.
- Mobile typecheck passes.
- Manual local-device test:
  1. Add/provision a device.
  2. Open device settings.
  3. Tap `Prepare device for transfer`.
  4. Confirm release.
  5. Verify device disappears immediately.
  6. Pull refresh.
  7. Restart app.
  8. Hold hardware button for 15 seconds.
  9. Verify device remains absent from the original account.

