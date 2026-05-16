Feature request: Notifications and alerts for PlantLab.

Context:
PlantLab has working device telemetry, mobile app, GCP backend, and updated hardware sensors.

Goal:
Design and implement a first version of alerts/notifications for important plant/device events.

Use workflow:
Planner → approval → Coder → Tester → Reviewer → Release Agent

Planner only:
- Study current backend telemetry model.
- Study mobile app notification capability.
- Study device status/readings.
- Do not implement yet.
- Create a plan only.

Initial alert types:
1. Device offline.
2. Water temperature too high/low.
3. Water level low.
4. Camera image upload missing/stale.
5. Sensor data stale.
6. Firmware/device error if diagnostics exist.

Keep alerts simple for MVP:
- in-app alerts first
- push notifications can be planned as phase 2 if setup is not ready
- avoid overbuilding rule engine

Planner should investigate:
- backend alert generation strategy
- alert thresholds
- per-device alert settings
- mobile alert list UI
- push notification readiness
- Expo notification requirements if used
- alert deduplication
- alert resolved state
- noisy alert prevention

Backend requirements:
- create alert records
- mark alert resolved
- avoid duplicate spam
- expose alerts to mobile/web
- possibly run scheduled alert check

Mobile requirements:
- show alert list/badge
- show device alert state
- allow dismiss/acknowledge if appropriate
- clear copy for user

Security/privacy:
- do not expose other users’ alerts
- do not leak device tokens
- auth required for alert APIs

Tester should verify:
- alert generation logic
- duplicate prevention
- resolved/active state
- mobile rendering with no alerts/many alerts
- auth protection
- no unrelated backend/device behavior changes

Reviewer should block if:
- alerts spam users
- alerts are not scoped per user/device
- thresholds are hardcoded without clear plan
- push notifications are added prematurely without reliable setup
- mobile UI becomes noisy

Release Agent should verify:
- backend migration risk
- scheduled job/deployment needs
- mobile build needs
- notification permission implications
- rollout/rollback notes

Planner output format:
1. Current alert readiness summary
2. Recommended MVP alert architecture
3. Alert types and thresholds
4. Backend data model/API plan
5. Mobile UI plan
6. Push notification decision
7. Deduplication/resolution strategy
8. Files likely to change
9. Implementation phases
10. Test plan
11. Release/deployment considerations
12. Risks and assumptions

Stop after writing the plan.
Do not implement until I approve.