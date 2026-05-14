# Local Agent Workflow

Everything for the local four-agent workflow lives in this folder.

The workflow is task-scoped:

- task inputs live in `tasks/`
- outputs and history live in `outputs/<task_id>/`
- `active_task.txt` selects which task the scripts operate on

## Quick Start

Create a task:

```bash
python agent-workspace/scripts/create_task.py 005_new_feature --activate
```

Edit:

```text
agent-workspace/tasks/005_new_feature.md
```

Run planner:

```bash
python agent-workspace/scripts/run_planner.py
```

Review:

```text
agent-workspace/outputs/005_new_feature/plan.md
```

Approve:

```bash
touch agent-workspace/outputs/005_new_feature/APPROVED_PLAN
```

Run pipeline:

```bash
python agent-workspace/scripts/run_pipeline.py
```

Review:

```text
agent-workspace/outputs/005_new_feature/final_summary.md
agent-workspace/outputs/005_new_feature/review.md
git diff
```

## Switch Tasks

```bash
python agent-workspace/scripts/set_active_task.py 002_ble_hardening
```

## Safe Preflight

```bash
python agent-workspace/scripts/run_pipeline.py --check
```

This validates active task resolution, approval, model selection, and detected test commands without running coder/tester/reviewer agents.

## Layout

```text
agent-workspace/
  active_task.txt
  tasks/
  outputs/
  prompts/
  scripts/
```

Each output folder contains:

```text
plan.md
coder_log.md
tester_log.md
test_report.md
review.md
final_summary.md
state.json
progress.log
heartbeat.json
current_stage.txt
tmp/
```

The approval marker is:

```text
outputs/<task_id>/APPROVED_PLAN
```

`APPROVED_PLAN`, runtime monitoring files, and `tmp/` are ignored by git. The root of each output folder is reserved for human-facing artifacts. Agent scratch files, per-attempt outputs, command logs, and other temporary artifacts are moved under `outputs/<task_id>/tmp/` after pipeline completion or failure.

## Monitoring A Run

Watch task progress:

```bash
tail -f agent-workspace/outputs/<task_id>/progress.log
```

Check the current stage:

```bash
cat agent-workspace/outputs/<task_id>/current_stage.txt
```

Check heartbeat status:

```bash
cat agent-workspace/outputs/<task_id>/heartbeat.json
```

The orchestrator updates heartbeat and progress at least every 30 seconds while an agent or test command is active. Coder runs in visible phases: repo analysis, file identification, implementation, build, tests, and fix pass.

`progress.log` is intentionally compact. It records stage changes, heartbeat messages, command start/end summaries, and subprocess output counts. Raw stdout/stderr lines are not written there; detailed output is capped into `coder_log.md`, `tester_log.md`, `test_report.md`, `review.md`, or files under `tmp/`.

## Runtime Defaults

- model: `gpt-5.5`
- planner timeout: `900` seconds
- coder analyze timeout: `900` seconds
- coder implement timeout: `2700` seconds
- coder cleanup timeout: `900` seconds
- tester timeout: `1200` seconds
- reviewer timeout: `900` seconds
- agent commits: disabled by default

Defaults live in:

```text
agent-workspace/workflow_config.json
```

Optional timeout overrides:

```bash
CODEX_WORKFLOW_MODEL=gpt-5.5
CODEX_WORKFLOW_TIMEOUT_CODER_IMPLEMENT_FEATURE=2700
CODEX_WORKFLOW_TIMEOUT_SECONDS=900
```

## Output Flood Protection

Agents are instructed not to print full diffs or full file contents. They should summarize with:

```bash
git diff --stat
git diff --name-only
```

The orchestrator also caps terminal display and `progress.log` growth. Useful output-cap overrides:

```bash
CODEX_WORKFLOW_MAX_TERMINAL_OUTPUT_CHARS=20000
CODEX_WORKFLOW_MAX_PROGRESS_LOG_BYTES=150000
CODEX_WORKFLOW_MAX_CAPTURED_OUTPUT_CHARS=80000
```

## Dirty Workspace And Commits

The pipeline refuses to run when the repo has uncommitted changes or local commits ahead of upstream.

Review state safely:

```bash
git status --short
git log --oneline --decorate -5
git diff --stat
```

Run in a dirty workspace only after manual approval:

```bash
python agent-workspace/scripts/run_pipeline.py --allow-dirty
```

Agents must not create commits. If an agent changes `HEAD` while `allow_agent_commits=false`, the pipeline stops before Tester/Reviewer.

## Timeout Recovery

If an agent times out:

1. Do not push generated commits.
2. Inspect `outputs/<task_id>/final_summary.md`.
3. Inspect `outputs/<task_id>/heartbeat.json`.
4. Inspect `outputs/<task_id>/progress.log`.
5. Review concise git state with `git status --short`, `git log --oneline --decorate -5`, and `git diff --stat`.
6. Fix orchestration or split the task before retrying.
