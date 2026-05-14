Feature request: Simplify BLE onboarding UX and fix Wi-Fi SSID selection fallback.

Context:
BLE provisioning is now working. This is a major milestone.

Now improve the onboarding experience so the user does less manual work.

Goals:
1. Remove the need for the user to scan or manually enter device serial number during onboarding.
2. Improve Wi-Fi SSID selection UX because Wi-Fi scanning/dropdown still does not work reliably.
3. Keep manual SSID entry as a fallback.

Use existing multi-agent workflow:
Planner → approval → Coder → Tester → Reviewer

Planner only:
- Study the current BLE provisioning flow.
- Study mobile app onboarding screens.
- Study backend device registration / claim flow.
- Study firmware BLE provisioning protocol.
- Do not implement yet.
- Create a plan only.

Part 1: Remove QR/serial-number step
Current issue:
The app currently asks the user to scan QR code or provide serial/device ID. This feels unnecessary because the mobile app is already connected to the device over BLE during provisioning.

Desired behavior:
- Mobile app connects to PlantLab device over BLE.
- Device provides its device identity over BLE, such as:
  - serial number
  - device_id
  - hardware id
  - firmware version
  - BLE device name
  - MAC-derived identifier if appropriate
- Mobile app sends this identity to backend during claim/registration.
- Backend binds the physical device to the logged-in user.
- User should not need to scan QR code for serial number in normal flow.

Planner should decide:
- What device identity should be exposed over BLE.
- Whether firmware already has serial/device ID available.
- Whether backend should accept device identity from mobile app during claim.
- Whether QR code should remain as fallback/debug path.
- How to prevent spoofing or accidental wrong-device registration.
- How to handle multiple nearby PlantLab devices.

Part 2: Wi-Fi SSID selection improvement
Current issue:
Home Wi-Fi dropdown/list still does not work reliably, so user must manually type SSID.

Planner should investigate and recommend one approach:
A. Fix ESP32 Wi-Fi scan over BLE and send SSID list to app.
B. Use iOS/native app capabilities if possible.
C. Keep manual SSID input as primary for now, but improve UX.
D. Hybrid: try scan, then fallback to manual input.

Important reality:
- iOS apps generally cannot freely scan nearby Wi-Fi SSIDs like Android.
- ESP32 only sees 2.4 GHz Wi-Fi.
- Manual SSID entry may need to remain as reliable fallback.
- The app should clearly explain 2.4 GHz requirement.

Desired Wi-Fi UX:
- Show “Scanning nearby 2.4 GHz Wi-Fi…” if scan is supported.
- If scan fails or returns empty:
  - show clear explanation
  - allow manual SSID entry
  - optionally remember recently used SSID locally
- Never block provisioning just because scan list is empty.
- Do not remove manual SSID input.

Part 3: Overall onboarding polish
Improve user flow:
1. User opens app.
2. User chooses Add Device.
3. App scans for PlantLab BLE devices.
4. User selects nearby PlantLab device.
5. App reads device identity over BLE.
6. App asks for Wi-Fi credentials.
7. App sends Wi-Fi credentials + claim/session token to device.
8. Device connects to Wi-Fi and registers with backend.
9. Backend links device to user.
10. App shows success screen.

Security requirements:
- Do not log Wi-Fi password.
- Do not log full tokens.
- Mask device token / claim token in logs.
- Avoid trusting only a public serial number if that creates spoofing risk.
- Keep existing production auth behavior intact.
- Do not expose secrets over unauthenticated channels more than current design requires.

Testing requirements:
Tester should verify:
- QR/serial step is not required in normal BLE flow.
- Device identity can be read from BLE or safely passed through provisioning.
- Backend claim/registration still works.
- Manual QR/serial fallback still works if kept.
- Wi-Fi manual SSID fallback works.
- Empty Wi-Fi scan result does not block provisioning.
- Multiple device scenario is handled clearly.
- No secrets are logged.
- Existing BLE provisioning still works.

Reviewer should block if:
- QR/serial fallback is removed without safe replacement.
- Backend can register arbitrary spoofed serials without protection.
- User can accidentally claim wrong nearby device too easily.
- Manual SSID fallback is removed.
- iOS Wi-Fi scan limitation is ignored.
- Existing BLE provisioning is broken.
- Production auth is changed unnecessarily.
- Secrets are logged.

Planner output format:
1. Current onboarding flow summary
2. Pain points
3. Recommended new onboarding flow
4. Device identity over BLE design
5. Backend claim/registration changes
6. QR/serial fallback decision
7. Wi-Fi SSID selection strategy
8. UX copy and screen changes
9. Security considerations
10. Files likely to change
11. Implementation steps
12. Test plan
13. Manual hardware validation checklist
14. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.
