# Decision Log

This is an append-only record of important decisions.

## 2026-05-17

- Decision: Replace the legacy in-repo `agent-workspace/` orchestration folder with Pantheon project control.
- Reason: Pantheon is now the reusable agent workflow, and PlantOS should not carry the older local coding-agent implementation.
- Consequence: `agent-workspace/` is removed from the repository. Pantheon target state lives under `.pantheon/`, with runtime folders ignored by git.

## 2026-05-19

- Decision: Represent grow LED dimming as a capability-gated `light:set_intensity` command carrying a 0-100 percent value.
- Reason: Existing on/off commands must remain compatible with simple relay hardware, while PWM-capable LED drivers need a clear backend/device contract.
- Consequence: Apps expose intensity controls only when node capabilities report support; devices without support continue to use on/off commands only.
