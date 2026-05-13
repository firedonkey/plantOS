# Local Agent Workflow

Everything for the local four-agent workflow lives in this folder.

Structure:

- `task.md`
- `plan.md`
- `APPROVED_PLAN.example`
- `APPROVED_PLAN`
- `coder_log.md`
- `tester_log.md`
- `test_report.md`
- `review.md`
- `final_summary.md`
- `state.json`
- `prompts/`
- `scripts/`

Usage:

1. Edit `task.md`
2. Run:
   - `python agent-workspace/scripts/run_planner.py`
3. Review:
   - `agent-workspace/plan.md`
4. Approve:
   - `cp agent-workspace/APPROVED_PLAN.example agent-workspace/APPROVED_PLAN`
5. Run:
   - `python agent-workspace/scripts/run_pipeline.py`
6. Review:
   - `agent-workspace/final_summary.md`
   - `agent-workspace/review.md`
   - `git diff`

Safe preflight:

- `python agent-workspace/scripts/run_pipeline.py --check`

This validates the workspace, model selection, approval marker, and detected test commands without running coder/tester/reviewer agents.

Runtime defaults:

- model: `gpt-5.5`
- per-agent timeout: `900` seconds

Optional overrides:

- `CODEX_WORKFLOW_MODEL=gpt-5.5`
- `CODEX_WORKFLOW_TIMEOUT_SECONDS=900`

The scripts treat a timeout as successful only when `codex exec` already wrote the expected output file. Otherwise the run fails and writes the blocker to the relevant workspace log.
