## Local Agent Workflow

This repository includes a local, file-based four-agent workflow under `/Users/gary/plantOS/agent-workspace`.

Roles:

1. `Planner Agent`
   - reads `agent-workspace/task.md`
   - writes `agent-workspace/plan.md`
   - must not edit production code
   - planning stops and waits for explicit user approval

2. `Coder Agent`
   - implements only the approved plan
   - writes a handoff summary to `agent-workspace/coder_log.md`

3. `Tester Agent`
   - adds or updates tests only
   - may update test harness files
   - writes a handoff summary to `agent-workspace/tester_log.md`
   - the wrapper script also runs detected project tests and writes `agent-workspace/test_report.md`

4. `Reviewer Agent`
   - reviews the current repo state against the task, plan, and test report
   - must not edit code
   - writes `agent-workspace/review.md`
   - first line must be `APPROVED` or `BLOCKED`

Files used as the communication layer:

- `agent-workspace/task.md`
- `agent-workspace/plan.md`
- `agent-workspace/APPROVED_PLAN`
- `agent-workspace/coder_log.md`
- `agent-workspace/tester_log.md`
- `agent-workspace/test_report.md`
- `agent-workspace/review.md`
- `agent-workspace/final_summary.md`
- `agent-workspace/state.json`

Entry points:

1. Edit `agent-workspace/task.md`
2. Run `python agent-workspace/scripts/run_planner.py`
3. Review `agent-workspace/plan.md`
4. Approve by creating `agent-workspace/APPROVED_PLAN`
5. Run `python agent-workspace/scripts/run_pipeline.py`
6. Review `agent-workspace/final_summary.md`, `agent-workspace/review.md`, and `git diff`
