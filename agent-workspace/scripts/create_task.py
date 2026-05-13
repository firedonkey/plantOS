#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from workflow_progress import ensure_monitoring_files


WORKSPACE = Path(__file__).resolve().parents[1]
TASKS_DIR = WORKSPACE / "tasks"
OUTPUTS_DIR = WORKSPACE / "outputs"
ACTIVE_TASK_PATH = WORKSPACE / "active_task.txt"
TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def title_from_task_id(task_id: str) -> str:
    parts = task_id.split("_")
    if parts and parts[0].isdigit():
        parts = parts[1:]
    title = " ".join(part.capitalize() for part in parts) or task_id
    return title


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def default_state() -> str:
    return json.dumps(
        {
            "status": "idle",
            "planner": {},
            "pipeline": {"attempt": 0, "max_retries": 3, "result": None},
        },
        indent=2,
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new local agent task.")
    parser.add_argument("task_id", help="Task id, for example 005_new_feature")
    parser.add_argument("--activate", action="store_true", help="Also set this task as active.")
    args = parser.parse_args()

    task_id = args.task_id.strip()
    if not TASK_ID_PATTERN.match(task_id):
        raise SystemExit(f"invalid task id: {task_id}")

    task_path = TASKS_DIR / f"{task_id}.md"
    output_dir = OUTPUTS_DIR / task_id
    title = title_from_task_id(task_id)

    created: list[Path] = []
    if write_if_missing(task_path, f"# {title}\n\nDescribe the task here.\n"):
        created.append(task_path)

    defaults = {
        output_dir / "plan.md": "# Plan\n\nPlanner output will be written here.\n",
        output_dir / "coder_log.md": "# Coder Log\n\n",
        output_dir / "tester_log.md": "# Tester Log\n\n",
        output_dir / "test_report.md": "# Test Report\n\n",
        output_dir / "review.md": "# Review\n\n",
        output_dir / "final_summary.md": "# Final Summary\n\n",
        output_dir / "state.json": default_state(),
    }
    for path, content in defaults.items():
        if write_if_missing(path, content):
            created.append(path)
    ensure_monitoring_files(output_dir, task_id)

    if args.activate:
        ACTIVE_TASK_PATH.write_text(task_id + "\n", encoding="utf-8")

    print(f"Task ready: {task_id}")
    print(f"Task file: {task_path}")
    print(f"Output folder: {output_dir}")
    if created:
        print("Created:")
        for path in created:
            print(f"- {path}")
    else:
        print("No files created; task already existed.")
    if args.activate:
        print(f"Active task set to {task_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
