#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from workflow_progress import (
    append_progress,
    ensure_monitoring_files,
    mark_stage,
    run_streaming_process,
    update_stage,
    write_heartbeat,
)


WORKSPACE = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKSPACE.parent
PROMPTS = WORKSPACE / "prompts"
TASKS_DIR = WORKSPACE / "tasks"
OUTPUTS_DIR = WORKSPACE / "outputs"
ACTIVE_TASK_PATH = WORKSPACE / "active_task.txt"
PLANNER_PROMPT_PATH = PROMPTS / "planner.md"
CONFIG_PATH = WORKSPACE / "workflow_config.json"
DEFAULT_CODEX_MODEL = "gpt-5.5"
DEFAULT_PLANNER_TIMEOUT_SECONDS = 900
TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class TaskContext:
    task_id: str
    task_path: Path
    output_dir: Path
    plan_path: Path
    state_path: Path


def workflow_timeout_seconds() -> int:
    default = DEFAULT_PLANNER_TIMEOUT_SECONDS
    if CONFIG_PATH.exists():
        try:
            config = json.loads(read_text(CONFIG_PATH))
            default = int((config.get("timeouts") or {}).get("planner", default))
        except (json.JSONDecodeError, TypeError, ValueError):
            raise SystemExit(f"invalid workflow config JSON: {CONFIG_PATH}")
    raw_value = os.environ.get("CODEX_WORKFLOW_TIMEOUT_PLANNER") or os.environ.get("CODEX_WORKFLOW_TIMEOUT_SECONDS")
    if raw_value is None:
        return default
    try:
        return max(1, int(raw_value))
    except ValueError:
        raise SystemExit("CODEX_WORKFLOW_TIMEOUT_PLANNER must be an integer")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def default_state() -> dict:
    return {
        "status": "idle",
        "planner": {},
        "pipeline": {"attempt": 0, "max_retries": 3, "result": None},
    }


def write_state(context: TaskContext, data: dict) -> None:
    write_text(context.state_path, json.dumps(data, indent=2) + "\n")


def load_state(context: TaskContext) -> dict:
    if not context.state_path.exists():
        return default_state()
    return json.loads(read_text(context.state_path))


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
    return TaskContext(
        task_id=task_id,
        task_path=task_path,
        output_dir=output_dir,
        plan_path=output_dir / "plan.md",
        state_path=output_dir / "state.json",
    )


def ensure_prereqs(context: TaskContext) -> str:
    codex_bin = shutil.which("codex")
    if not codex_bin:
        raise SystemExit("codex executable not found in PATH")
    if not PLANNER_PROMPT_PATH.exists():
        raise SystemExit(f"missing planner prompt: {PLANNER_PROMPT_PATH}")
    return codex_bin


def build_prompt(context: TaskContext) -> str:
    prompt = read_text(PLANNER_PROMPT_PATH).rstrip()
    task = read_text(context.task_path).strip()
    return (
        f"{prompt}\n\n"
        "Repository root:\n"
        f"{REPO_ROOT}\n\n"
        "Current task id:\n"
        f"{context.task_id}\n\n"
        "Current task file:\n"
        f"{context.task_path}\n\n"
        "Current task output folder:\n"
        f"{context.output_dir}\n\n"
        "Task:\n"
        "```md\n"
        f"{task}\n"
        "```\n\n"
        f"Output only the plan content for {context.plan_path}. "
        "Do not edit any repository files. Stop after planning."
    )


def run_codex(context: TaskContext, codex_bin: str, prompt: str, plan_path: Path) -> tuple[subprocess.CompletedProcess[str], bool]:
    model = os.environ.get("CODEX_WORKFLOW_MODEL", DEFAULT_CODEX_MODEL)
    cmd = [
        codex_bin,
        "exec",
        "-",
        "--cd",
        str(REPO_ROOT),
        "--model",
        model,
        "--sandbox",
        "read-only",
        "--output-last-message",
        str(plan_path),
        "--color",
        "never",
    ]
    timeout_seconds = workflow_timeout_seconds()
    return run_streaming_process(
        cmd,
        cwd=REPO_ROOT,
        input_text=prompt,
        timeout_seconds=timeout_seconds,
        output_dir=context.output_dir,
        task_id=context.task_id,
        agent="planner",
        stage="planning",
    )


def main() -> int:
    context = task_context()
    codex_bin = ensure_prereqs(context)
    prompt = build_prompt(context)
    plan_before = read_text(context.plan_path)
    mark_stage(context.output_dir, context.task_id, "planner", "planning", "running planner agent")
    result, timed_out = run_codex(context, codex_bin, prompt, context.plan_path)
    plan_after = read_text(context.plan_path)
    output_written = bool(plan_after.strip()) and plan_after != plan_before
    if result.returncode != 0 and not (timed_out and output_written):
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        if timed_out:
            sys.stderr.write(
                "\ncodex exec timed out without writing a new plan.\n"
            )
        write_heartbeat(context.output_dir, context.task_id, "planner", "planning", "failed", "planner failed")
        append_progress(context.output_dir, "planner", "planner failed")
        return result.returncode
    state = load_state(context)
    state["status"] = "waiting_for_approval"
    state["active_task"] = context.task_id
    state["planner"] = {
        "completed_at": utc_now(),
        "task_file": str(context.task_path),
        "output_dir": str(context.output_dir),
        "plan_file": str(context.plan_path),
        "model": os.environ.get("CODEX_WORKFLOW_MODEL", DEFAULT_CODEX_MODEL),
        "timed_out_after_output": timed_out and output_written,
    }
    state["pipeline"] = {"attempt": 0, "max_retries": 3, "result": None}
    write_state(context, state)
    update_stage(context.output_dir, "waiting for approval")
    write_heartbeat(context.output_dir, context.task_id, "planner", "waiting_for_approval", "completed", "planner completed; waiting for approval")
    append_progress(context.output_dir, "planner", f"planner completed; wrote {context.plan_path}")
    print(f"Active task: {context.task_id}")
    print(f"Wrote plan to {context.plan_path}")
    if timed_out and output_written:
        print("Planner output was written before codex exec timed out; treated as successful.")
    print(f"Planner stopped. Review the plan and create {context.output_dir / 'APPROVED_PLAN'} to continue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
