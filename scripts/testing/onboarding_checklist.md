# PlantLab Real Device Onboarding Checklist

Use this short checklist while executing
`docs/testing/onboarding_validation_plan.md`.

## Before Testing

- [ ] Local backend is running.
- [ ] Provisioning backend is running.
- [ ] iPhone can reach the laptop API URL.
- [ ] Mobile app is installed and points to the correct API URL.
- [ ] Master firmware version recorded.
- [ ] Camera firmware version recorded.
- [ ] Device starting ownership state recorded.
- [ ] Backend logs are ready.
- [ ] Firmware serial logs are ready if hardware is connected.
- [ ] Screen recording is enabled if testing failure recovery.

## Per Scenario

- [ ] Scenario name recorded.
- [ ] Start time recorded.
- [ ] Device prepared to required starting state.
- [ ] Test executed once without changing code.
- [ ] Completion or failure time recorded.
- [ ] Number of taps recorded.
- [ ] Number of retries recorded.
- [ ] User-facing messages copied exactly.
- [ ] Recovery action recorded.
- [ ] Device online result recorded.
- [ ] Heartbeat result recorded.
- [ ] Image result recorded if relevant.
- [ ] Issue filed if result is fail or blocked.

## First Test Order

- [ ] Happy path
- [ ] Wrong password
- [ ] Factory reset
- [ ] Ownership conflict
- [ ] BLE disconnect
- [ ] Weak Wi-Fi
- [ ] App backgrounding
- [ ] Device reboot during setup

## After Testing

- [ ] Logs attached to issues.
- [ ] Screenshots or screen recordings attached.
- [ ] Device restored to known state.
- [ ] Pass/fail summary updated.
- [ ] Critical or high issues reviewed before GCP deployment.
