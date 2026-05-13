#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKSPACE.parent
PROMPTS = WORKSPACE / "prompts"
STATE_PATH = WORKSPACE / "state.json"
TASK_PATH = WORKSPACE / "task.md"
PLAN_PATH = WORKSPACE / "plan.md"
PLANNER_PROMPT_PATH = PROMPTS / "planner.md"
DEFAULT_CODEX_MODEL = "gpt-5.4"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_state(data: dict) -> None:
    STATE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {
            "status": "idle",
            "planner": {},
            "pipeline": {"attempt": 0, "max_retries": 3, "result": None},
        }
    return json.loads(read_text(STATE_PATH))


def ensure_prereqs() -> str:
    codex_bin = shutil.which("codex")
    if not codex_bin:
        raise SystemExit("codex executable not found in PATH")
    if not TASK_PATH.exists():
        raise SystemExit(f"missing task file: {TASK_PATH}")
    task = read_text(TASK_PATH).strip()
    if not task:
        raise SystemExit(f"task file is empty: {TASK_PATH}")
    if not PLANNER_PROMPT_PATH.exists():
        raise SystemExit(f"missing planner prompt: {PLANNER_PROMPT_PATH}")
    return codex_bin


def build_prompt(task: str) -> str:
    prompt = read_text(PLANNER_PROMPT_PATH).rstrip()
    return (
        f"{prompt}\n\n"
        "Repository root:\n"
        f"{REPO_ROOT}\n\n"
        "Task from agent-workspace/task.md:\n"
        "```md\n"
        f"{task}\n"
        "```\n\n"
        "Output only the plan content for agent-workspace/plan.md. "
        "Do not edit any repository files. Stop after planning."
    )


def run_codex(codex_bin: str, prompt: str) -> subprocess.CompletedProcess[str]:
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
        str(PLAN_PATH),
        "--color",
        "never",
    ]
    return subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def main() -> int:
    codex_bin = ensure_prereqs()
    task = read_text(TASK_PATH).strip()
    prompt = build_prompt(task)
    result = run_codex(codex_bin, prompt)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode
    state = load_state()
    state["status"] = "waiting_for_approval"
    state["planner"] = {
        "completed_at": utc_now(),
        "task_file": str(TASK_PATH),
        "plan_file": str(PLAN_PATH),
    }
    state["pipeline"] = {"attempt": 0, "max_retries": 3, "result": None}
    write_state(state)
    print(f"Wrote plan to {PLAN_PATH}")
    print("Planner stopped after plan generation. Review the plan and create APPROVED_PLAN to continue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
