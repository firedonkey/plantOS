# Decision Log

This is an append-only record of important decisions.

## 2026-05-17

- Decision: Replace the legacy in-repo `agent-workspace/` orchestration folder with Pantheon project control.
- Reason: Pantheon is now the reusable agent workflow, and PlantOS should not carry the older local coding-agent implementation.
- Consequence: `agent-workspace/` is removed from the repository. Pantheon target state lives under `.pantheon/`, with runtime folders ignored by git.
