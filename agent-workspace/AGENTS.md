## Local Multi-Agent Workflow

This repository uses a local, file-based four-agent workflow under `agent-workspace/`.
It does not require GitHub or any remote issue tracker.

## Architecture

Agents:

1. `Planner Agent`
   - Reads the active task from `agent-workspace/tasks/<task_id>.md`
   - Writes `agent-workspace/outputs/<task_id>/plan.md`
   - Must not edit production code
   - Stops after planning and waits for explicit approval

2. `Coder Agent`
   - Implements only the approved plan
   - Writes `agent-workspace/outputs/<task_id>/coder_log.md`

3. `Tester Agent`
   - Adds or updates tests where appropriate
   - Runs available checks through the wrapper pipeline
   - Writes `agent-workspace/outputs/<task_id>/tester_log.md`
   - Test command output goes to `agent-workspace/outputs/<task_id>/test_report.md`

4. `Reviewer Agent`
   - Reviews the current repo state against the task, plan, coder log, tester log, and test report
   - Must not edit code
   - Writes `agent-workspace/outputs/<task_id>/review.md`
   - First line must be exactly `APPROVED` or `BLOCKED`

## File Layout

```text
agent-workspace/
  active_task.txt
  tasks/
    001_ble_provisioning.md
    002_ble_hardening.md
    003_camera_reliability.md
    004_espnow_retry.md
  outputs/
    001_ble_provisioning/
      plan.md
      APPROVED_PLAN
      coder_log.md
      tester_log.md
      test_report.md
      review.md
      final_summary.md
      state.json
      progress.log
      heartbeat.json
      current_stage.txt
  prompts/
    planner.md
    coder.md
    tester.md
    reviewer.md
  scripts/
    create_task.py
    set_active_task.py
    run_planner.py
    run_pipeline.py
```

`APPROVED_PLAN`, per-attempt scratch logs, and runtime monitoring files are local ignored files.

## Progress And Heartbeat Files

Every task output folder has three monitoring files:

```text
agent-workspace/outputs/<task_id>/progress.log
agent-workspace/outputs/<task_id>/heartbeat.json
agent-workspace/outputs/<task_id>/current_stage.txt
```

`progress.log` is capped human-readable progress. The orchestrator appends:

```text
[2026-05-13 10:31:12] [coder] analyzing repo
[2026-05-13 10:32:41] [coder] still running; current stage: implementing feature
```

`heartbeat.json` is the machine-readable current status:

```json
{
  "task_id": "002_ble_hardening",
  "agent": "coder",
  "stage": "implementing feature",
  "status": "running",
  "last_update": "2026-05-13T17:32:00+00:00",
  "message": "still running; current stage: implementing feature"
}
```

Valid heartbeat statuses are:

- `running`
- `completed`
- `failed`

`current_stage.txt` is a short human-readable stage, such as:

```text
running project tests
```

The orchestrator updates heartbeat and progress at least every 30 seconds while a subprocess is active. Agent prompts also instruct agents to update these files at major milestones when the sandbox allows it.

Secrets must never be written to progress files. The orchestrator applies basic redaction to common token/password patterns, but agents should avoid logging secrets in the first place.

## Terminal Visibility

Long-running subprocess output is streamed live. The pipeline also prints periodic messages:

```text
[coder] still running; current stage: implementing feature
[tester] still running; current stage: running tests: pytest
```

Subprocess stdout/stderr is also appended to `progress.log`, with basic secret redaction.
Terminal display is capped so a noisy agent cannot flood the terminal. The progress log is also capped and keeps the recent tail when it grows too large.

The output caps can be overridden with:

```bash
CODEX_WORKFLOW_MAX_TERMINAL_OUTPUT_CHARS=60000
CODEX_WORKFLOW_MAX_PROGRESS_LOG_BYTES=1000000
CODEX_WORKFLOW_MAX_CAPTURED_OUTPUT_CHARS=160000
CODEX_WORKFLOW_MAX_PROGRESS_MESSAGE_CHARS=8000
```

## Phased Coder Execution

The Coder Agent runs in smaller phases instead of one large opaque pass:

1. `analyze_repo`
2. `plan_file_changes`
3. `implement_feature`
4. `cleanup_and_self_check`

Each phase has a visible stage in `current_stage.txt`, writes progress entries, and has its own scratch output file under the task output directory. The combined coder output is still appended to `coder_log.md`, preserving the existing Coder → Tester → Reviewer architecture.

Coder phases must not print full diffs or full file contents. They should summarize with:

```bash
git diff --stat
git diff --name-only
```

## Timeout Config

Timeouts are configured in `agent-workspace/workflow_config.json`.

Defaults:

```json
{
  "allow_agent_commits": false,
  "timeouts": {
    "planner": 900,
    "coder.analyze_repo": 900,
    "coder.plan_file_changes": 900,
    "coder.implement_feature": 2700,
    "coder.cleanup_and_self_check": 900,
    "tester": 1200,
    "reviewer": 900
  }
}
```

Environment variables override config values for one run:

```bash
CODEX_WORKFLOW_TIMEOUT_PLANNER=900
CODEX_WORKFLOW_TIMEOUT_CODER_IMPLEMENT_FEATURE=2700
CODEX_WORKFLOW_TIMEOUT_TESTER=1200
CODEX_WORKFLOW_TIMEOUT_REVIEWER=900
```

`CODEX_WORKFLOW_TIMEOUT_SECONDS` remains a global fallback override.

## No-Agent-Commit Rule

Agents must not create commits by default.

`agent-workspace/workflow_config.json` defaults to:

```json
{
  "allow_agent_commits": false
}
```

The orchestrator records `HEAD` before each agent run. If an agent changes `HEAD` while commits are disabled, the pipeline marks the run failed and stops before the next agent.

## Dirty Workspace Safety

Before running the pipeline, the orchestrator checks for:

- uncommitted changes
- local commits ahead of the configured upstream branch

The pipeline refuses to run unless the workspace is clean. To intentionally run in a dirty workspace:

```bash
python agent-workspace/scripts/run_pipeline.py --allow-dirty
```

Use `--allow-dirty` only after manually reviewing the current git state.

## Debugging Stuck Agents

If a run appears stuck:

1. Check the terminal for `[agent] still running...` messages.
2. Read `agent-workspace/outputs/<task_id>/current_stage.txt`.
3. Read `agent-workspace/outputs/<task_id>/heartbeat.json`.
4. Tail the progress log:

```bash
tail -f agent-workspace/outputs/<task_id>/progress.log
```

If `heartbeat.json` has not changed for more than a few minutes and the terminal shows no process output, the child process may be blocked. The orchestrator will mark the heartbeat `failed` if the configured timeout is reached.

If a run times out:

1. Read `agent-workspace/outputs/<task_id>/final_summary.md`.
2. Read the latest `heartbeat.json` and `current_stage.txt`.
3. Inspect concise git state:

```bash
git status --short
git log --oneline --decorate -5
git diff --stat
```

4. Do not push local commits created by a failed agent run until they have been reviewed and split or repaired.
5. Fix orchestration problems first, then rerun with `--allow-dirty` only if the dirty state is intentional.

## Task Flow

1. Create or edit a task file in `agent-workspace/tasks/`.
2. Set the active task in `agent-workspace/active_task.txt`.
3. Run the Planner Agent.
4. Review `agent-workspace/outputs/<task_id>/plan.md`.
5. Approve by creating `agent-workspace/outputs/<task_id>/APPROVED_PLAN`.
6. Run the pipeline.
7. Review `final_summary.md`, `review.md`, and `git diff`.

## Create A Task

```bash
python agent-workspace/scripts/create_task.py 005_new_feature
```

Create and activate in one step:

```bash
python agent-workspace/scripts/create_task.py 005_new_feature --activate
```

## Switch Active Task

```bash
python agent-workspace/scripts/set_active_task.py 002_ble_hardening
```

This updates:

```text
agent-workspace/active_task.txt
```

## Run Planner

```bash
python agent-workspace/scripts/run_planner.py
```

The planner reads the active task and writes:

```text
agent-workspace/outputs/<task_id>/plan.md
```

## Approve Plan

After reviewing the plan:

```bash
touch agent-workspace/outputs/<task_id>/APPROVED_PLAN
```

You can also put a short approval note in that file.

## Run Pipeline

```bash
python agent-workspace/scripts/run_pipeline.py
```

Safe preflight:

```bash
python agent-workspace/scripts/run_pipeline.py --check
```

Resume after a completed coder handoff:

```bash
python agent-workspace/scripts/run_pipeline.py --resume-after-coder
```

## Runtime Defaults

- `CODEX_WORKFLOW_MODEL` defaults to `gpt-5.5`
- `CODEX_WORKFLOW_TIMEOUT_SECONDS` defaults to `900`

The scripts fail closed when a required task, plan, approval marker, or prompt is missing.
