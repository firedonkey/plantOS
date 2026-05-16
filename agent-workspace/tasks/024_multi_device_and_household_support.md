Feature request: Multi-device and household support for PlantLab.

Context:
PlantLab currently supports core single-device flow. Next, prepare the product for users who may own multiple PlantLab units or share access with household members.

Goal:
Add or prepare support for:
- multiple PlantLab devices per user
- cleaner device switching
- household/shared access model
- future multi-user collaboration

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current user/device data model.
- Study auth/session model.
- Study mobile device list and dashboard navigation.
- Study backend ownership/claiming logic.
- Do not implement yet.
- Create a plan only.

MVP requirements:
1. A user can own multiple PlantLab devices.
2. Mobile app can list all user devices.
3. User can switch between devices.
4. Device dashboard clearly shows selected device.
5. Device claiming does not overwrite existing devices.
6. Device deletion/unlink behavior is defined.

Household support planning:
- decide whether to implement now or design for later
- possible model:
  - household
  - household_members
  - device belongs to household
  - roles: owner/admin/viewer
- avoid overbuilding if not needed yet

Planner should investigate:
- current backend schema
- whether device ownership is user-based or account-based
- current mobile device list behavior
- provisioning/claiming assumptions
- API authorization risks
- migration impact

Backend requirements:
- device list API
- selected device/detail API
- claim device safely
- prevent cross-user access
- support ownership/unlink flow

Mobile requirements:
- device list screen
- selected device state
- dashboard per device
- empty state for no devices
- add-device entry point
- clear device name/edit name if appropriate

Security:
- user must not access another user’s device
- device claim flow must prevent hijacking
- household sharing must have role rules if implemented

Tester should verify:
- multiple devices display correctly
- switching devices works
- dashboard uses selected device only
- unauthorized access is blocked
- provisioning new device does not break existing device
- no duplicate/broken ownership state

Reviewer should block if:
- cross-user data leak is possible
- selected device state is fragile
- backend ownership model is unclear
- provisioning flow breaks existing devices
- household feature is overbuilt without need

Release Agent should verify:
- migration risk
- auth/authorization risk
- mobile UX readiness
- rollback notes
- manual validation checklist

Planner output format:
1. Current single/multi-device readiness summary
2. Recommended MVP multi-device model
3. Household support decision
4. Backend schema/API plan
5. Mobile UX/navigation plan
6. Provisioning/claiming impact
7. Security/authorization plan
8. Migration/backward compatibility plan
9. Files likely to change
10. Implementation phases
11. Test plan
12. Release/deployment considerations
13. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.