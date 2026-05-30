# PlantLab Onboarding Issue Template

Use this template for every issue found during real-device onboarding validation.
Keep the report short, factual, and reproducible.

## Issue ID

`ONB-YYYYMMDD-NN`

## Date

YYYY-MM-DD HH:MM local time

## Reporter

Name:

## Device

- Master hardware ID:
- Camera hardware ID:
- Master board:
- Camera board:
- Serial ports used:

## Firmware Version

- Master:
- Camera:

## App Version

- iOS version:
- Mobile app build:
- API target:
- Account used:

## Scenario

Name from validation matrix:

Starting state:

- Unclaimed
- Claimed by same account
- Claimed by another account
- Released for transfer
- Factory reset
- Offline
- Other:

## Expected Behavior

Describe what should have happened.

## Actual Behavior

Describe what happened, including exact user-facing copy.

## Severity

Choose one:

- Critical: blocks onboarding or risks wrong-account ownership.
- High: onboarding fails but has a workaround.
- Medium: confusing UX or recovery path, but setup can continue.
- Low: cosmetic copy or layout issue.

## Screenshots / Screen Recording

Attach links or filenames:

## Logs

Backend logs:

```text
Paste relevant provisioning/platform log lines here.
```

Master firmware logs:

```text
Paste relevant master serial log lines here.
```

Camera firmware logs:

```text
Paste relevant camera serial log lines here.
```

Mobile notes:

```text
Paste visible app state transitions or console notes here.
```

## Reproducibility

Choose one:

- Always
- Often
- Sometimes
- Once
- Unknown

Steps to reproduce:

1.
2.
3.

## Timing

- Onboarding start time:
- Failure or completion time:
- Total duration:
- Number of taps:
- Number of retries:

## Recovery Result

- Recovery action attempted:
- Recovery succeeded: yes/no
- Device appeared online: yes/no
- First heartbeat received: yes/no
- First image received: yes/no

## Suggested Fix

Proposed fix or investigation path:

## Owner / Status

- Owner:
- Status:
- Follow-up PR/commit:
