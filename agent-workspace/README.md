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
