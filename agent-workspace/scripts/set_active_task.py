#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from workflow_progress import ensure_monitoring_files


WORKSPACE = Path(__file__).resolve().parents[1]
TASKS_DIR = WORKSPACE / "tasks"
OUTPUTS_DIR = WORKSPACE / "outputs"
ACTIVE_TASK_PATH = WORKSPACE / "active_task.txt"
TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Switch the active local agent task.")
    parser.add_argument("task_id", help="Task id, for example 002_ble_hardening")
    args = parser.parse_args()

    task_id = args.task_id.strip()
    if not TASK_ID_PATTERN.match(task_id):
        raise SystemExit(f"invalid task id: {task_id}")

    task_path = TASKS_DIR / f"{task_id}.md"
    if not task_path.exists():
        raise SystemExit(f"task does not exist: {task_path}")

    output_dir = OUTPUTS_DIR / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_monitoring_files(output_dir, task_id)
    ACTIVE_TASK_PATH.write_text(task_id + "\n", encoding="utf-8")
    print(f"Active task set to {task_id}")
    print(f"Task file: {task_path}")
    print(f"Output folder: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
