#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from workflow_progress import (
    append_progress,
    cleanup_output_root,
    ensure_monitoring_files,
    mark_stage,
    run_streaming_process,
    temp_output_path,
    update_stage,
    write_heartbeat,
)


WORKSPACE = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKSPACE.parent
PROMPTS = WORKSPACE / "prompts"
TASKS_DIR = WORKSPACE / "tasks"
OUTPUTS_DIR = WORKSPACE / "outputs"
ACTIVE_TASK_PATH = WORKSPACE / "active_task.txt"

CODER_PROMPT_PATH = PROMPTS / "coder.md"
TESTER_PROMPT_PATH = PROMPTS / "tester.md"
REVIEWER_PROMPT_PATH = PROMPTS / "reviewer.md"
CONFIG_PATH = WORKSPACE / "workflow_config.json"

MAX_RETRIES = 3
DEFAULT_CODEX_MODEL = "gpt-5.5"
DEFAULT_TIMEOUTS = {
    "planner": 900,
    "coder.analyze_repo": 900,
    "coder.plan_file_changes": 900,
    "coder.implement_feature": 2700,
    "coder.cleanup_and_self_check": 900,
    "tester": 1200,
    "reviewer": 900,
}
MAX_PROMPT_SECTION_CHARS = 20000
MAX_PROCESS_OUTPUT_CHARS = 12000
TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
CODER_PHASES = [
    (
        "analyze_repo",
        "Repo analysis only. Inspect the relevant repository structure and summarize what must change. Do not edit files in this phase.",
        "analyzing repo",
        "coder.analyze_repo",
    ),
    (
        "plan_file_changes",
        "Identify the files and local tests/builds needed for this implementation. Produce a concise file-change plan. Do not edit files in this phase.",
        "planning file changes",
        "coder.plan_file_changes",
    ),
    (
        "implement_feature",
        "Implement only the approved plan and current pipeline feedback. Keep changes scoped. Do not run broad test suites in this phase.",
        "implementing feature",
        "coder.implement_feature",
    ),
    (
        "cleanup_and_self_check",
        "Run concise self-checks, summarize changed files using git diff --stat/name-only, and fix only obvious issues caused by this change. Do not print full diffs or commit.",
        "cleanup and self-check",
        "coder.cleanup_and_self_check",
    ),
]


@dataclass(frozen=True)
class TaskContext:
    task_id: str
    task_path: Path
    output_dir: Path
    plan_path: Path
    approved_plan_path: Path
    coder_log_path: Path
    tester_log_path: Path
    test_report_path: Path
    review_path: Path
    final_summary_path: Path
    state_path: Path


@dataclass
class TestCommand:
    label: str
    cmd: list[str]
    cwd: Path


@dataclass
class AgentRunResult:
    process: subprocess.CompletedProcess[str]
    timed_out: bool
    output_written: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_workflow_config() -> dict:
    config = {
        "allow_agent_commits": False,
        "timeouts": dict(DEFAULT_TIMEOUTS),
    }
    if CONFIG_PATH.exists():
        try:
            user_config = json.loads(read_text(CONFIG_PATH))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid workflow config JSON: {CONFIG_PATH}: {exc}")
        if isinstance(user_config, dict):
            if "allow_agent_commits" in user_config:
                config["allow_agent_commits"] = bool(user_config["allow_agent_commits"])
            if isinstance(user_config.get("timeouts"), dict):
                for key, value in user_config["timeouts"].items():
                    if key in config["timeouts"]:
                        try:
                            config["timeouts"][key] = max(1, int(value))
                        except (TypeError, ValueError):
                            raise SystemExit(f"invalid timeout for {key} in {CONFIG_PATH}")
    return config


def workflow_timeout_seconds(key: str) -> int:
    config = load_workflow_config()
    default = int(config["timeouts"].get(key, DEFAULT_TIMEOUTS.get(key, 900)))
    env_key = "CODEX_WORKFLOW_TIMEOUT_" + re.sub(r"[^A-Z0-9]+", "_", key.upper()).strip("_")
    raw_value = os.environ.get(env_key) or os.environ.get("CODEX_WORKFLOW_TIMEOUT_SECONDS")
    if raw_value is None:
        return default
    try:
        return max(1, int(raw_value))
    except ValueError:
        raise SystemExit(f"{env_key} must be an integer")


def allow_agent_commits() -> bool:
    return bool(load_workflow_config().get("allow_agent_commits", False))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def bounded_text(path: Path, max_chars: int = MAX_PROMPT_SECTION_CHARS) -> str:
    content = read_text(path).strip()
    if len(content) <= max_chars:
        return content
    omitted = len(content) - max_chars
    return (
        f"[truncated {omitted} chars from the beginning; showing the most recent {max_chars} chars]\n"
        + content[-max_chars:]
    )


def truncate_for_log(content: str, max_chars: int = MAX_PROCESS_OUTPUT_CHARS) -> str:
    if len(content) <= max_chars:
        return content
    omitted = len(content) - max_chars
    return (
        f"[truncated {omitted} chars from the middle]\n"
        + content[: max_chars // 2]
        + "\n...\n"
        + content[-(max_chars // 2) :]
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)


def default_state() -> dict:
    return {
        "status": "idle",
        "planner": {},
        "pipeline": {"attempt": 0, "max_retries": MAX_RETRIES, "result": None},
    }


def read_active_task_id() -> str:
    if not ACTIVE_TASK_PATH.exists():
        raise SystemExit(f"missing active task file: {ACTIVE_TASK_PATH}")
    task_id = read_text(ACTIVE_TASK_PATH).strip()
    if not task_id:
        raise SystemExit(f"active task file is empty: {ACTIVE_TASK_PATH}")
    if not TASK_ID_PATTERN.match(task_id):
        raise SystemExit(f"invalid active task id: {task_id}")
    return task_id


def task_context() -> TaskContext:
    task_id = read_active_task_id()
    task_path = TASKS_DIR / f"{task_id}.md"
    if not task_path.exists():
        raise SystemExit(f"active task does not exist: {task_path}")
    if not read_text(task_path).strip():
        raise SystemExit(f"active task file is empty: {task_path}")
    output_dir = OUTPUTS_DIR / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_monitoring_files(output_dir, task_id)
    cleanup_output_root(output_dir)
    return TaskContext(
        task_id=task_id,
        task_path=task_path,
        output_dir=output_dir,
        plan_path=output_dir / "plan.md",
        approved_plan_path=output_dir / "APPROVED_PLAN",
        coder_log_path=output_dir / "coder_log.md",
        tester_log_path=output_dir / "tester_log.md",
        test_report_path=output_dir / "test_report.md",
        review_path=output_dir / "review.md",
        final_summary_path=output_dir / "final_summary.md",
        state_path=output_dir / "state.json",
    )


def load_state(context: TaskContext) -> dict:
    if not context.state_path.exists():
        return default_state()
    return json.loads(read_text(context.state_path))


def write_state(context: TaskContext, state: dict) -> None:
    write_text(context.state_path, json.dumps(state, indent=2) + "\n")


def ensure_output_files(context: TaskContext) -> None:
    defaults = {
        context.plan_path: "# Plan\n\n",
        context.coder_log_path: "# Coder Log\n\n",
        context.tester_log_path: "# Tester Log\n\n",
        context.test_report_path: "# Test Report\n\n",
        context.review_path: "# Review\n\n",
        context.final_summary_path: "# Final Summary\n\n",
        context.state_path: json.dumps(default_state(), indent=2) + "\n",
        context.output_dir / "progress.log": "",
        context.output_dir / "current_stage.txt": "idle\n",
    }
    for path, content in defaults.items():
        if not path.exists():
            write_text(path, content)
    ensure_monitoring_files(context.output_dir, context.task_id)
    cleanup_output_root(context.output_dir)


def ensure_workspace(context: TaskContext) -> str:
    ensure_output_files(context)
    codex_bin = shutil.which("codex")
    if not codex_bin:
        raise SystemExit("codex executable not found in PATH")
    for path in [
        context.task_path,
        context.plan_path,
        context.approved_plan_path,
        CODER_PROMPT_PATH,
        TESTER_PROMPT_PATH,
        REVIEWER_PROMPT_PATH,
    ]:
        if not path.exists():
            raise SystemExit(f"missing required file: {path}")
    if not read_text(context.task_path).strip():
        raise SystemExit(f"task file is empty: {context.task_path}")
    if not read_text(context.plan_path).strip():
        raise SystemExit(f"plan file is empty: {context.plan_path}")
    if not read_text(context.approved_plan_path).strip():
        raise SystemExit(f"approval file is empty: {context.approved_plan_path}")
    return codex_bin


def git_output(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def current_head() -> str:
    result = git_output(["rev-parse", "HEAD"], check=True)
    return result.stdout.strip()


def workspace_safety_status() -> dict:
    status = git_output(["status", "--porcelain"])
    upstream = git_output(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    upstream_name = upstream.stdout.strip() if upstream.returncode == 0 else ""
    ahead_count = 0
    behind_count = 0
    if upstream_name:
        ahead = git_output(["rev-list", "--left-right", "--count", f"{upstream_name}...HEAD"])
        if ahead.returncode == 0:
            parts = ahead.stdout.strip().split()
            if len(parts) == 2:
                behind_count = int(parts[0])
                ahead_count = int(parts[1])
    return {
        "dirty": bool(status.stdout.strip()),
        "dirty_summary": status.stdout.strip().splitlines()[:80],
        "upstream": upstream_name,
        "ahead_count": ahead_count,
        "behind_count": behind_count,
    }


def enforce_workspace_safety(allow_dirty: bool) -> None:
    safety = workspace_safety_status()
    if allow_dirty:
        if safety["dirty"] or safety["ahead_count"]:
            print(
                "WARNING: running with --allow-dirty. "
                f"dirty={safety['dirty']} ahead={safety['ahead_count']} upstream={safety['upstream'] or 'none'}"
            )
        return
    if not safety["dirty"] and safety["ahead_count"] == 0:
        return

    lines = [
        "Refusing to run pipeline because the workspace is not clean.",
        "",
        f"- Uncommitted changes: {'yes' if safety['dirty'] else 'no'}",
        f"- Local commits ahead of upstream: {safety['ahead_count']}",
        f"- Upstream: {safety['upstream'] or 'not configured'}",
        "",
        "Clean/stash/split the work manually, or rerun with --allow-dirty after you intentionally approve this state.",
    ]
    if safety["dirty_summary"]:
        lines.extend(["", "Dirty summary:"])
        lines.extend(f"  {line}" for line in safety["dirty_summary"])
    raise SystemExit("\n".join(lines))


def detect_unexpected_agent_commit(before_head: str, *, agent: str) -> bool:
    after_head = current_head()
    if after_head == before_head:
        return False
    return not allow_agent_commits()


def check_workspace(context: TaskContext) -> int:
    codex_bin = ensure_workspace(context)
    mark_stage(context.output_dir, context.task_id, "orchestrator", "checking workflow", "running workflow preflight check")
    model = os.environ.get("CODEX_WORKFLOW_MODEL", DEFAULT_CODEX_MODEL)
    config = load_workflow_config()
    commands = detect_test_commands()
    safety = workspace_safety_status()
    lines = [
        "# Final Summary",
        "",
        "- Status: CHECK PASSED",
        "- No agents were run.",
        "- No production code was changed by this check.",
        f"- Active task: `{context.task_id}`",
        f"- Task file: `{context.task_path}`",
        f"- Output folder: `{context.output_dir}`",
        f"- Codex binary: `{codex_bin}`",
        f"- Model: `{model}`",
        f"- Agent commits allowed: `{config['allow_agent_commits']}`",
        "",
        "## Timeouts",
        "",
    ]
    for key, value in config["timeouts"].items():
        lines.append(f"- {key}: {value}s")
    lines.extend([
        "",
        "## Workspace Safety",
        "",
        f"- Uncommitted changes: {'yes' if safety['dirty'] else 'no'}",
        f"- Local commits ahead of upstream: {safety['ahead_count']}",
        f"- Upstream: {safety['upstream'] or 'not configured'}",
        "",
        "## Detected test commands",
        "",
    ])
    if commands:
        for command in commands:
            lines.append(f"- {command.label}: `{' '.join(command.cmd)}` in `{command.cwd}`")
    else:
        lines.append("- No supported test command detected.")
    write_text(context.final_summary_path, "\n".join(lines) + "\n")
    state = load_state(context)
    state["status"] = "approved_ready"
    state["active_task"] = context.task_id
    state["pipeline"] = {
        "attempt": 0,
        "max_retries": MAX_RETRIES,
        "result": "check_passed",
        "checked_at": utc_now(),
        "model": model,
        "timeouts": config["timeouts"],
        "allow_agent_commits": config["allow_agent_commits"],
        "workspace_safety": safety,
    }
    write_state(context, state)
    update_stage(context.output_dir, "approved and ready")
    write_heartbeat(context.output_dir, context.task_id, "orchestrator", "approved_ready", "completed", "workflow check passed")
    append_progress(context.output_dir, "orchestrator", "workflow check passed")
    print(f"Workflow check passed for {context.task_id}. Wrote {context.final_summary_path}")
    return 0


def normalize_test_file(path: Path, title: str) -> None:
    write_text(path, f"# {title}\n\n")


def build_agent_prompt(
    context: TaskContext,
    prompt_path: Path,
    role_name: str,
    attempt: int,
    extra_feedback: str = "",
    phase_name: str | None = None,
    phase_instruction: str | None = None,
) -> str:
    task = read_text(context.task_path).strip()
    plan = read_text(context.plan_path).strip()
    approved = read_text(context.approved_plan_path).strip()
    coder_log = bounded_text(context.coder_log_path)
    tester_log = bounded_text(context.tester_log_path)
    test_report = bounded_text(context.test_report_path)
    review = bounded_text(context.review_path)
    base = read_text(prompt_path).rstrip()
    sections = [
        base,
        f"Repository root:\n{REPO_ROOT}",
        f"Current task id:\n{context.task_id}",
        f"Current task file:\n{context.task_path}",
        f"Current task output folder:\n{context.output_dir}",
        f"Attempt: {attempt} of {MAX_RETRIES}",
        f"Progress log:\n{context.output_dir / 'progress.log'}",
        f"Heartbeat file:\n{context.output_dir / 'heartbeat.json'}",
        f"Current stage file:\n{context.output_dir / 'current_stage.txt'}",
        "Task:\n```md\n" + task + "\n```",
        "Approved plan:\n```md\n" + plan + "\n```",
        "Approval marker:\n```md\n" + approved + "\n```",
    ]
    if coder_log:
        sections.append("Coder log so far:\n```md\n" + coder_log + "\n```")
    if tester_log:
        sections.append("Tester log so far:\n```md\n" + tester_log + "\n```")
    if test_report:
        sections.append("Test report so far:\n```md\n" + test_report + "\n```")
    if review:
        sections.append("Latest review:\n```md\n" + review + "\n```")
    if extra_feedback:
        sections.append("Pipeline feedback:\n```md\n" + extra_feedback.strip() + "\n```")
    if phase_name and phase_instruction:
        sections.append(
            "Current coder phase:\n"
            f"- Phase id: `{phase_name}`\n"
            f"- Phase instruction: {phase_instruction}\n"
            "\nFollow this phase boundary. Do not skip ahead unless the phase instruction says to implement or fix."
        )
    sections.append(
        "Output discipline:\n"
        "- Do not print full diffs, large patches, generated files, or full file contents.\n"
        "- Use concise summaries, `git diff --stat`, and `git diff --name-only`.\n"
        "- Do not create git commits unless the workflow config explicitly allows it."
    )
    if role_name == "Tester Agent":
        sections.append(
            f"The wrapper script will also run detected project tests after your step and append canonical output to {context.test_report_path}."
        )
    sections.append(f"Write only the final {role_name} output for its target markdown log file.")
    return "\n\n".join(sections)


def run_codex_agent(
    context: TaskContext,
    codex_bin: str,
    prompt_path: Path,
    output_path: Path,
    sandbox: str,
    attempt: int,
    role_name: str,
    extra_feedback: str = "",
    phase_name: str | None = None,
    phase_instruction: str | None = None,
    display_stage: str | None = None,
    timeout_key: str | None = None,
) -> AgentRunResult:
    model = os.environ.get("CODEX_WORKFLOW_MODEL", DEFAULT_CODEX_MODEL)
    prompt = build_agent_prompt(context, prompt_path, role_name, attempt, extra_feedback, phase_name, phase_instruction)
    output_before = read_text(output_path)
    cmd = [
        codex_bin,
        "exec",
        "-",
        "--cd",
        str(REPO_ROOT),
        "--model",
        model,
        "--sandbox",
        sandbox,
        "--output-last-message",
        str(output_path),
        "--color",
        "never",
    ]
    agent_label = role_name.replace(" Agent", "").lower()
    inferred_timeout_key = timeout_key or agent_label
    timeout_seconds = workflow_timeout_seconds(inferred_timeout_key)
    stage = display_stage or role_name.lower().replace(" ", "_")
    before_head = current_head()
    process_result, timed_out = run_streaming_process(
        cmd,
        cwd=REPO_ROOT,
        input_text=prompt,
        timeout_seconds=timeout_seconds,
        output_dir=context.output_dir,
        task_id=context.task_id,
        agent=agent_label,
        stage=stage,
    )
    if detect_unexpected_agent_commit(before_head, agent=agent_label):
        message = (
            f"{agent_label} changed HEAD from {before_head} to {current_head()} even though "
            "allow_agent_commits=false. Stopping before the next agent."
        )
        append_progress(context.output_dir, "orchestrator", message)
        write_heartbeat(context.output_dir, context.task_id, "orchestrator", "unexpected agent commit", "failed", message)
        process_result = subprocess.CompletedProcess(
            process_result.args,
            98,
            process_result.stdout,
            process_result.stderr + "\n" + message + "\n",
        )
    output_after = read_text(output_path)
    output_written = bool(output_after.strip()) and output_after != output_before
    return AgentRunResult(process_result, timed_out, output_written)


def append_agent_message(log_path: Path, output_path: Path) -> None:
    message = read_text(output_path).strip()
    if message:
        append_text(log_path, message + "\n\n")


def append_attempt_header(path: Path, title: str, attempt: int) -> None:
    append_text(path, f"## Attempt {attempt}\n\n### {title}\n\n")


def append_process_output(path: Path, result: AgentRunResult | subprocess.CompletedProcess[str]) -> None:
    process = result.process if isinstance(result, AgentRunResult) else result
    if isinstance(result, AgentRunResult) and result.timed_out:
        append_text(
            path,
            "#### timeout\n\ncodex exec exceeded its configured timeout. "
            f"Output written: {'yes' if result.output_written else 'no'}.\n\n",
        )
    if process.stdout:
        append_text(path, "#### stdout\n\n```\n" + truncate_for_log(process.stdout.rstrip()) + "\n```\n\n")
    if process.stderr:
        append_text(path, "#### stderr\n\n```\n" + truncate_for_log(process.stderr.rstrip()) + "\n```\n\n")


def agent_run_failed(result: AgentRunResult) -> bool:
    if result.timed_out:
        return True
    if result.process.returncode == 0:
        return False
    return True


def run_coder_phases(
    context: TaskContext,
    codex_bin: str,
    attempt: int,
    extra_feedback: str,
) -> AgentRunResult:
    last_result: AgentRunResult | None = None
    aggregate_parts: list[str] = []
    for phase_name, phase_instruction, display_stage, timeout_key in CODER_PHASES:
        append_progress(context.output_dir, "coder", f"starting phase {phase_name}: {display_stage}")
        update_stage(context.output_dir, display_stage)
        write_heartbeat(context.output_dir, context.task_id, "coder", display_stage, "running", f"starting phase {phase_name}")
        phase_output_path = temp_output_path(context.output_dir, f"coder_attempt_{attempt}_{phase_name}.md")
        phase_feedback = extra_feedback
        if last_result and agent_run_failed(last_result):
            phase_feedback = (
                phase_feedback
                + "\n\nPrevious coder phase failed. Stop and report the failure clearly; do not continue blindly."
            ).strip()
        result = run_codex_agent(
            context,
            codex_bin,
            CODER_PROMPT_PATH,
            phase_output_path,
            "workspace-write",
            attempt,
            "Coder Agent",
            phase_feedback,
            phase_name=phase_name,
            phase_instruction=phase_instruction,
            display_stage=display_stage,
            timeout_key=timeout_key,
        )
        append_text(context.coder_log_path, f"### Phase: {phase_name}\n\n")
        append_agent_message(context.coder_log_path, phase_output_path)
        phase_message = read_text(phase_output_path).strip()
        if phase_message:
            aggregate_parts.append(f"## Phase: {phase_name}\n\n{phase_message}\n")
        append_process_output(context.coder_log_path, result)
        last_result = result
        if agent_run_failed(result):
            append_progress(context.output_dir, "coder", f"phase {phase_name} failed")
            return result
        append_progress(context.output_dir, "coder", f"phase {phase_name} completed")

    assert last_result is not None
    write_text(temp_output_path(context.output_dir, f"coder_attempt_{attempt}.md"), "\n".join(aggregate_parts).strip() + "\n")
    write_heartbeat(context.output_dir, context.task_id, "coder", "coder phases completed", "completed", "all coder phases completed")
    update_stage(context.output_dir, "coder phases completed")
    return last_result


def existing_coder_attempt_path(context: TaskContext, attempt: int) -> Path:
    candidates = [
        temp_output_path(context.output_dir, f"coder_attempt_{attempt}.md"),
        temp_output_path(context.output_dir, f".coder_attempt_{attempt}.md"),
        context.output_dir / f".coder_attempt_{attempt}.md",
    ]
    for candidate in candidates:
        if read_text(candidate).strip():
            return candidate
    return candidates[0]


def find_python_for_pytest() -> list[str]:
    repo_python = REPO_ROOT / ".venv" / "bin" / "python"
    if repo_python.exists():
        return [str(repo_python), "-m", "pytest", "platform/backend/tests"]
    return [sys.executable, "-m", "pytest", "platform/backend/tests"]


def load_package_json(path: Path) -> dict:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def should_ignore_discovered_path(path: Path) -> bool:
    try:
        relative = path.relative_to(REPO_ROOT)
    except ValueError:
        return True
    ignored_parts = {
        ".git",
        ".pio-core",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
    }
    return any(part in ignored_parts for part in relative.parts)


def iter_package_tests() -> Iterable[TestCommand]:
    for package_path in sorted(REPO_ROOT.rglob("package.json")):
        if should_ignore_discovered_path(package_path):
            continue
        package = load_package_json(package_path)
        scripts = package.get("scripts") or {}
        if "test" not in scripts:
            continue
        cwd = package_path.parent
        if (cwd / "pnpm-lock.yaml").exists() or str(package.get("packageManager", "")).startswith("pnpm@"):
            if shutil.which("pnpm"):
                yield TestCommand(f"pnpm test ({cwd.relative_to(REPO_ROOT)})", ["pnpm", "test"], cwd)
        elif shutil.which("npm"):
            yield TestCommand(f"npm test ({cwd.relative_to(REPO_ROOT)})", ["npm", "test"], cwd)


def detect_test_commands() -> list[TestCommand]:
    commands: list[TestCommand] = []

    pytest_tests = REPO_ROOT / "platform" / "backend" / "tests"
    if pytest_tests.exists():
        commands.append(TestCommand("pytest", find_python_for_pytest(), REPO_ROOT))

    commands.extend(iter_package_tests())

    for cargo_toml in sorted(REPO_ROOT.rglob("Cargo.toml")):
        if should_ignore_discovered_path(cargo_toml):
            continue
        if shutil.which("cargo"):
            commands.append(TestCommand(f"cargo test ({cargo_toml.parent.relative_to(REPO_ROOT)})", ["cargo", "test"], cargo_toml.parent))

    for go_mod in sorted(REPO_ROOT.rglob("go.mod")):
        if should_ignore_discovered_path(go_mod):
            continue
        if shutil.which("go"):
            commands.append(TestCommand(f"go test ./... ({go_mod.parent.relative_to(REPO_ROOT)})", ["go", "test", "./..."], go_mod.parent))

    for pio_ini in sorted(REPO_ROOT.rglob("platformio.ini")):
        if should_ignore_discovered_path(pio_ini):
            continue
        if not (pio_ini.parent / "test").exists():
            continue
        pio_bin = shutil.which("pio")
        repo_pio = REPO_ROOT / ".venv" / "bin" / "pio"
        if not pio_bin and repo_pio.exists():
            pio_bin = str(repo_pio)
        if pio_bin:
            commands.append(TestCommand(f"platformio test ({pio_ini.parent.relative_to(REPO_ROOT)})", [pio_bin, "test"], pio_ini.parent))

    unique: list[TestCommand] = []
    seen: set[tuple[str, str]] = set()
    for command in commands:
        key = (" ".join(command.cmd), str(command.cwd))
        if key in seen:
            continue
        seen.add(key)
        unique.append(command)
    return unique


def run_test_commands(context: TaskContext, attempt: int) -> tuple[bool, list[dict]]:
    commands = detect_test_commands()
    mark_stage(context.output_dir, context.task_id, "tester", "running project tests", "running detected project tests")
    append_attempt_header(context.test_report_path, "Detected test commands", attempt)
    if not commands:
        append_text(context.test_report_path, "No supported test command was detected.\n\n")
        append_progress(context.output_dir, "tester", "no supported test command detected")
        return True, []
    overall_success = True
    results: list[dict] = []
    for test_command in commands:
        append_text(
            context.test_report_path,
            f"#### {test_command.label}\n\n"
            f"`cwd={test_command.cwd}`\n\n"
            f"`{' '.join(test_command.cmd)}`\n\n",
        )
        proc, timed_out = run_streaming_process(
            test_command.cmd,
            cwd=test_command.cwd,
            input_text=None,
            timeout_seconds=workflow_timeout_seconds("tester"),
            output_dir=context.output_dir,
            task_id=context.task_id,
            agent="tester",
            stage=f"running tests: {test_command.label}",
        )
        append_process_output(context.test_report_path, proc)
        success = proc.returncode == 0 and not timed_out
        overall_success = overall_success and success
        append_text(context.test_report_path, f"Result: {'PASS' if success else 'FAIL'}\n\n")
        results.append(
            {
                "label": test_command.label,
                "cwd": str(test_command.cwd),
                "cmd": test_command.cmd,
                "returncode": proc.returncode,
            }
        )
    return overall_success, results


def parse_review_status(context: TaskContext) -> str:
    status = "BLOCKED"
    review = read_text(context.review_path).splitlines()
    for line in review:
        normalized = line.strip().upper()
        if normalized in {"APPROVED", "BLOCKED"}:
            status = normalized
    return status


def summarize_results(
    context: TaskContext,
    success: bool,
    attempt: int,
    tests_ok: bool,
    review_status: str,
    test_results: list[dict],
) -> None:
    lines = [
        "# Final Summary",
        "",
        f"- Status: {'SUCCESS' if success else 'FAILED'}",
        f"- Active task: `{context.task_id}`",
        f"- Task file: `{context.task_path}`",
        f"- Output folder: `{context.output_dir}`",
        f"- Attempts used: {attempt}",
        f"- Tests status: {'PASS' if tests_ok else 'FAIL'}",
        f"- Reviewer status: {review_status}",
        "",
        "## Files to review",
        "",
        f"- {context.coder_log_path}",
        f"- {context.tester_log_path}",
        f"- {context.test_report_path}",
        f"- {context.review_path}",
        "",
        "## Detected test commands",
        "",
    ]
    if test_results:
        for result in test_results:
            lines.append(f"- {result['label']}: returncode={result['returncode']} cwd={result['cwd']}")
    else:
        lines.append("- No supported test command detected.")
    lines.extend(["", "## Next step", "", "- Review final_summary.md, review.md, and git diff."])
    write_text(context.final_summary_path, "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local agent pipeline.")
    parser.add_argument("--check", action="store_true", help="Validate workspace/model/test detection without running agents.")
    parser.add_argument("--resume-after-coder", action="store_true", help="Reuse outputs/<task_id>/.coder_attempt_1.md and continue with Tester/Reviewer.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow running with uncommitted changes or local commits ahead of upstream.")
    args = parser.parse_args()

    context = task_context()
    if args.check:
        return check_workspace(context)

    enforce_workspace_safety(args.allow_dirty)
    codex_bin = ensure_workspace(context)
    mark_stage(context.output_dir, context.task_id, "orchestrator", "pipeline starting", "starting approved pipeline")
    normalize_test_file(context.coder_log_path, "Coder Log")
    normalize_test_file(context.tester_log_path, "Tester Log")
    normalize_test_file(context.test_report_path, "Test Report")
    normalize_test_file(context.review_path, "Review")
    state = load_state(context)
    state["status"] = "pipeline_running"
    state["active_task"] = context.task_id
    state["pipeline"] = {"attempt": 0, "max_retries": MAX_RETRIES, "result": None, "started_at": utc_now()}
    write_state(context, state)

    extra_feedback = ""
    success = False
    final_tests_ok = False
    final_review_status = "BLOCKED"
    final_test_results: list[dict] = []

    for attempt in range(1, MAX_RETRIES + 1):
        state["pipeline"]["attempt"] = attempt
        write_state(context, state)

        coder_output_path = existing_coder_attempt_path(context, attempt)
        if args.resume_after_coder and attempt == 1:
            if not read_text(coder_output_path).strip():
                raise SystemExit(f"cannot resume after coder: missing {coder_output_path}")
            append_attempt_header(context.coder_log_path, "Coder Agent", attempt)
            append_text(context.coder_log_path, "Reused existing coder output from prior completed attempt.\n\n")
            append_agent_message(context.coder_log_path, coder_output_path)
        else:
            append_attempt_header(context.coder_log_path, "Coder Agent", attempt)
            coder_result = run_coder_phases(context, codex_bin, attempt, extra_feedback)
            if agent_run_failed(coder_result):
                state["status"] = "failed"
                state["pipeline"]["result"] = "coder_timed_out" if coder_result.timed_out else "coder_failed"
                write_state(context, state)
                write_heartbeat(context.output_dir, context.task_id, "coder", "coder failed", "failed", "coder agent failed")
                append_progress(context.output_dir, "coder", "coder agent failed")
                summarize_results(context, False, attempt, False, "BLOCKED", [])
                cleanup_output_root(context.output_dir)
                sys.stderr.write(truncate_for_log(coder_result.process.stdout))
                sys.stderr.write(truncate_for_log(coder_result.process.stderr))
                if coder_result.timed_out:
                    sys.stderr.write("\ncoder agent timed out without writing output.\n")
                return coder_result.process.returncode or 1

        mark_stage(context.output_dir, context.task_id, "tester", "tester agent", "starting tester agent")
        append_attempt_header(context.tester_log_path, "Tester Agent", attempt)
        tester_output_path = temp_output_path(context.output_dir, f"tester_attempt_{attempt}.md")
        tester_result = run_codex_agent(
            context,
            codex_bin,
            TESTER_PROMPT_PATH,
            tester_output_path,
            "workspace-write",
            attempt,
            "Tester Agent",
            extra_feedback,
            display_stage="tester agent",
            timeout_key="tester",
        )
        append_agent_message(context.tester_log_path, tester_output_path)
        append_process_output(context.tester_log_path, tester_result)
        if agent_run_failed(tester_result):
            state["status"] = "failed"
            state["pipeline"]["result"] = "tester_timed_out" if tester_result.timed_out else "tester_failed"
            write_state(context, state)
            write_heartbeat(context.output_dir, context.task_id, "tester", "tester failed", "failed", "tester agent failed")
            append_progress(context.output_dir, "tester", "tester agent failed")
            summarize_results(context, False, attempt, False, "BLOCKED", [])
            cleanup_output_root(context.output_dir)
            sys.stderr.write(truncate_for_log(tester_result.process.stdout))
            sys.stderr.write(truncate_for_log(tester_result.process.stderr))
            if tester_result.timed_out:
                sys.stderr.write("\ntester agent timed out without writing output.\n")
            return tester_result.process.returncode or 1

        tests_ok, test_results = run_test_commands(context, attempt)
        final_tests_ok = tests_ok
        final_test_results = test_results

        mark_stage(context.output_dir, context.task_id, "reviewer", "reviewer agent", "starting reviewer agent")
        append_attempt_header(context.review_path, "Reviewer Agent", attempt)
        reviewer_output_path = temp_output_path(context.output_dir, f"review_attempt_{attempt}.md")
        reviewer_feedback = extra_feedback
        if not tests_ok:
            reviewer_feedback = (reviewer_feedback + "\n\nTests failed. Review with that failure in mind.").strip()
        reviewer_result = run_codex_agent(
            context,
            codex_bin,
            REVIEWER_PROMPT_PATH,
            reviewer_output_path,
            "read-only",
            attempt,
            "Reviewer Agent",
            reviewer_feedback,
            display_stage="reviewer agent",
            timeout_key="reviewer",
        )
        append_agent_message(context.review_path, reviewer_output_path)
        append_process_output(context.review_path, reviewer_result)
        if agent_run_failed(reviewer_result):
            state["status"] = "failed"
            state["pipeline"]["result"] = "reviewer_timed_out" if reviewer_result.timed_out else "reviewer_failed"
            write_state(context, state)
            write_heartbeat(context.output_dir, context.task_id, "reviewer", "reviewer failed", "failed", "reviewer agent failed")
            append_progress(context.output_dir, "reviewer", "reviewer agent failed")
            summarize_results(context, False, attempt, tests_ok, "BLOCKED", test_results)
            cleanup_output_root(context.output_dir)
            sys.stderr.write(truncate_for_log(reviewer_result.process.stdout))
            sys.stderr.write(truncate_for_log(reviewer_result.process.stderr))
            if reviewer_result.timed_out:
                sys.stderr.write("\nreviewer agent timed out without writing output.\n")
            return reviewer_result.process.returncode or 1

        review_status = parse_review_status(context)
        final_review_status = review_status
        if tests_ok and review_status == "APPROVED":
            success = True
            state["status"] = "completed"
            state["pipeline"]["result"] = "approved"
            state["pipeline"]["completed_at"] = utc_now()
            write_state(context, state)
            update_stage(context.output_dir, "pipeline completed")
            write_heartbeat(context.output_dir, context.task_id, "orchestrator", "pipeline completed", "completed", "pipeline completed successfully")
            append_progress(context.output_dir, "orchestrator", f"pipeline completed successfully after attempt {attempt}")
            summarize_results(context, True, attempt, tests_ok, review_status, test_results)
            cleanup_output_root(context.output_dir)
            print(f"Pipeline completed successfully for {context.task_id} after attempt {attempt}")
            return 0

        extra_feedback = (
            "Pipeline requires another coder pass.\n\n"
            f"Tests status: {'PASS' if tests_ok else 'FAIL'}\n"
            f"Reviewer status: {review_status}\n\n"
            "Use the latest test report and review findings as the sole rework input."
        )
        append_progress(context.output_dir, "orchestrator", f"attempt {attempt} requires another coder pass")

    state["status"] = "failed"
    state["pipeline"]["result"] = "max_retries_exhausted"
    state["pipeline"]["completed_at"] = utc_now()
    write_state(context, state)
    update_stage(context.output_dir, "pipeline failed")
    write_heartbeat(context.output_dir, context.task_id, "orchestrator", "pipeline failed", "failed", "max retries exhausted")
    append_progress(context.output_dir, "orchestrator", "pipeline failed after max retries")
    summarize_results(context, success, MAX_RETRIES, final_tests_ok, final_review_status, final_test_results)
    cleanup_output_root(context.output_dir)
    print(f"Pipeline failed for {context.task_id} after max retries.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
