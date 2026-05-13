#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


WORKSPACE = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKSPACE.parent
PROMPTS = WORKSPACE / "prompts"
STATE_PATH = WORKSPACE / "state.json"

TASK_PATH = WORKSPACE / "task.md"
PLAN_PATH = WORKSPACE / "plan.md"
APPROVED_PLAN_PATH = WORKSPACE / "APPROVED_PLAN"
CODER_LOG_PATH = WORKSPACE / "coder_log.md"
TESTER_LOG_PATH = WORKSPACE / "tester_log.md"
TEST_REPORT_PATH = WORKSPACE / "test_report.md"
REVIEW_PATH = WORKSPACE / "review.md"
FINAL_SUMMARY_PATH = WORKSPACE / "final_summary.md"

CODER_PROMPT_PATH = PROMPTS / "coder.md"
TESTER_PROMPT_PATH = PROMPTS / "tester.md"
REVIEWER_PROMPT_PATH = PROMPTS / "reviewer.md"

MAX_RETRIES = 3
DEFAULT_CODEX_MODEL = "gpt-5.4"


@dataclass
class TestCommand:
    label: str
    cmd: list[str]
    cwd: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def append_text(path: Path, content: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {
            "status": "idle",
            "planner": {},
            "pipeline": {"attempt": 0, "max_retries": MAX_RETRIES, "result": None},
        }
    return json.loads(read_text(STATE_PATH))


def write_state(state: dict) -> None:
    write_text(STATE_PATH, json.dumps(state, indent=2) + "\n")


def ensure_workspace() -> str:
    codex_bin = shutil.which("codex")
    if not codex_bin:
        raise SystemExit("codex executable not found in PATH")
    for path in [TASK_PATH, PLAN_PATH, APPROVED_PLAN_PATH, CODER_PROMPT_PATH, TESTER_PROMPT_PATH, REVIEWER_PROMPT_PATH]:
        if not path.exists():
            raise SystemExit(f"missing required file: {path}")
    if not read_text(TASK_PATH).strip():
        raise SystemExit(f"task file is empty: {TASK_PATH}")
    if not read_text(PLAN_PATH).strip():
        raise SystemExit(f"plan file is empty: {PLAN_PATH}")
    if not read_text(APPROVED_PLAN_PATH).strip():
        raise SystemExit(f"approval file is empty: {APPROVED_PLAN_PATH}")
    return codex_bin


def normalize_test_file(path: Path, title: str) -> None:
    write_text(path, f"# {title}\n\n")


def build_agent_prompt(prompt_path: Path, role_name: str, attempt: int, extra_feedback: str = "") -> str:
    task = read_text(TASK_PATH).strip()
    plan = read_text(PLAN_PATH).strip()
    approved = read_text(APPROVED_PLAN_PATH).strip()
    coder_log = read_text(CODER_LOG_PATH).strip()
    tester_log = read_text(TESTER_LOG_PATH).strip()
    test_report = read_text(TEST_REPORT_PATH).strip()
    review = read_text(REVIEW_PATH).strip()
    base = read_text(prompt_path).rstrip()
    sections = [
        base,
        f"Repository root:\n{REPO_ROOT}",
        f"Attempt: {attempt} of {MAX_RETRIES}",
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
    if role_name == "Tester Agent":
        sections.append(
            "The wrapper script will also run detected project tests after your step and append the canonical output to agent-workspace/test_report.md."
        )
    sections.append(f"Write only the final {role_name} output for its target markdown log file.")
    return "\n\n".join(sections)


def run_codex_agent(
    codex_bin: str,
    prompt_path: Path,
    output_path: Path,
    sandbox: str,
    attempt: int,
    role_name: str,
    extra_feedback: str = "",
) -> subprocess.CompletedProcess[str]:
    model = os.environ.get("CODEX_WORKFLOW_MODEL", DEFAULT_CODEX_MODEL)
    prompt = build_agent_prompt(prompt_path, role_name, attempt, extra_feedback)
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
    return subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def append_agent_message(log_path: Path, output_path: Path) -> None:
    message = read_text(output_path).strip()
    if message:
        append_text(log_path, message + "\n\n")


def append_attempt_header(path: Path, title: str, attempt: int) -> None:
    append_text(path, f"## Attempt {attempt}\n\n### {title}\n\n")


def append_process_output(path: Path, result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        append_text(path, "#### stdout\n\n```\n" + result.stdout.rstrip() + "\n```\n\n")
    if result.stderr:
        append_text(path, "#### stderr\n\n```\n" + result.stderr.rstrip() + "\n```\n\n")


def find_python_for_pytest() -> list[str] | None:
    repo_python = REPO_ROOT / ".venv" / "bin" / "python"
    if repo_python.exists():
        return [str(repo_python), "-m", "pytest", "platform/backend/tests"]
    return [sys.executable, "-m", "pytest", "platform/backend/tests"]


def load_package_json(path: Path) -> dict:
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def iter_package_tests() -> Iterable[TestCommand]:
    for package_path in sorted(REPO_ROOT.rglob("package.json")):
        if "node_modules" in package_path.parts:
            continue
        package = load_package_json(package_path)
        scripts = package.get("scripts") or {}
        if "test" not in scripts:
            continue
        cwd = package_path.parent
        if (cwd / "pnpm-lock.yaml").exists() or str(package.get("packageManager", "")).startswith("pnpm@"):
            if shutil.which("pnpm"):
                yield TestCommand(f"pnpm test ({cwd.relative_to(REPO_ROOT)})", ["pnpm", "test"], cwd)
        else:
            if shutil.which("npm"):
                yield TestCommand(f"npm test ({cwd.relative_to(REPO_ROOT)})", ["npm", "test"], cwd)


def detect_test_commands() -> list[TestCommand]:
    commands: list[TestCommand] = []

    pytest_tests = REPO_ROOT / "platform" / "backend" / "tests"
    if pytest_tests.exists():
        commands.append(TestCommand("pytest", find_python_for_pytest(), REPO_ROOT))

    commands.extend(iter_package_tests())

    for cargo_toml in sorted(REPO_ROOT.rglob("Cargo.toml")):
        if shutil.which("cargo"):
            commands.append(TestCommand(f"cargo test ({cargo_toml.parent.relative_to(REPO_ROOT)})", ["cargo", "test"], cargo_toml.parent))

    for go_mod in sorted(REPO_ROOT.rglob("go.mod")):
        if shutil.which("go"):
            commands.append(TestCommand(f"go test ./... ({go_mod.parent.relative_to(REPO_ROOT)})", ["go", "test", "./..."], go_mod.parent))

    for pio_ini in sorted(REPO_ROOT.rglob("platformio.ini")):
        if shutil.which("pio"):
            commands.append(TestCommand(f"platformio test ({pio_ini.parent.relative_to(REPO_ROOT)})", ["pio", "test"], pio_ini.parent))

    unique: list[TestCommand] = []
    seen: set[tuple[str, str]] = set()
    for command in commands:
        key = (" ".join(command.cmd), str(command.cwd))
        if key in seen:
            continue
        seen.add(key)
        unique.append(command)
    return unique


def run_test_commands(attempt: int) -> tuple[bool, list[dict]]:
    commands = detect_test_commands()
    append_attempt_header(TEST_REPORT_PATH, "Detected test commands", attempt)
    if not commands:
        append_text(TEST_REPORT_PATH, "No supported test command was detected.\n\n")
        return True, []
    overall_success = True
    results: list[dict] = []
    for test_command in commands:
        append_text(
            TEST_REPORT_PATH,
            f"#### {test_command.label}\n\n"
            f"`cwd={test_command.cwd}`\n\n"
            f"`{' '.join(test_command.cmd)}`\n\n",
        )
        proc = subprocess.run(
            test_command.cmd,
            cwd=test_command.cwd,
            text=True,
            capture_output=True,
        )
        append_process_output(TEST_REPORT_PATH, proc)
        success = proc.returncode == 0
        overall_success = overall_success and success
        append_text(TEST_REPORT_PATH, f"Result: {'PASS' if success else 'FAIL'}\n\n")
        results.append(
            {
                "label": test_command.label,
                "cwd": str(test_command.cwd),
                "cmd": test_command.cmd,
                "returncode": proc.returncode,
            }
        )
    return overall_success, results


def parse_review_status() -> str:
    status = "BLOCKED"
    review = read_text(REVIEW_PATH).splitlines()
    for line in review:
        normalized = line.strip().upper()
        if normalized in {"APPROVED", "BLOCKED"}:
            status = normalized
    return status


def summarize_results(
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
        f"- Attempts used: {attempt}",
        f"- Tests status: {'PASS' if tests_ok else 'FAIL'}",
        f"- Reviewer status: {review_status}",
        "",
        "## Files to review",
        "",
        f"- {CODER_LOG_PATH}",
        f"- {TESTER_LOG_PATH}",
        f"- {TEST_REPORT_PATH}",
        f"- {REVIEW_PATH}",
        "",
        "## Detected test commands",
        "",
    ]
    if test_results:
        for result in test_results:
            lines.append(
                f"- {result['label']}: returncode={result['returncode']} cwd={result['cwd']}"
            )
    else:
        lines.append("- No supported test command detected.")
    lines.extend(
        [
            "",
            "## Next step",
            "",
            "- Review final_summary.md, review.md, and git diff.",
        ]
    )
    write_text(FINAL_SUMMARY_PATH, "\n".join(lines) + "\n")


def main() -> int:
    codex_bin = ensure_workspace()
    normalize_test_file(CODER_LOG_PATH, "Coder Log")
    normalize_test_file(TESTER_LOG_PATH, "Tester Log")
    normalize_test_file(TEST_REPORT_PATH, "Test Report")
    normalize_test_file(REVIEW_PATH, "Review")
    state = load_state()
    state["status"] = "pipeline_running"
    state["pipeline"] = {"attempt": 0, "max_retries": MAX_RETRIES, "result": None, "started_at": utc_now()}
    write_state(state)

    extra_feedback = ""
    success = False
    final_tests_ok = False
    final_review_status = "BLOCKED"
    final_test_results: list[dict] = []

    for attempt in range(1, MAX_RETRIES + 1):
        state["pipeline"]["attempt"] = attempt
        write_state(state)

        append_attempt_header(CODER_LOG_PATH, "Coder Agent", attempt)
        coder_output_path = WORKSPACE / f".coder_attempt_{attempt}.md"
        coder_result = run_codex_agent(
            codex_bin,
            CODER_PROMPT_PATH,
            coder_output_path,
            "workspace-write",
            attempt,
            "Coder Agent",
            extra_feedback,
        )
        append_agent_message(CODER_LOG_PATH, coder_output_path)
        append_process_output(CODER_LOG_PATH, coder_result)
        if coder_result.returncode != 0:
            state["status"] = "failed"
            state["pipeline"]["result"] = "coder_failed"
            write_state(state)
            summarize_results(False, attempt, False, "BLOCKED", [])
            sys.stderr.write(coder_result.stdout)
            sys.stderr.write(coder_result.stderr)
            return coder_result.returncode

        append_attempt_header(TESTER_LOG_PATH, "Tester Agent", attempt)
        tester_output_path = WORKSPACE / f".tester_attempt_{attempt}.md"
        tester_result = run_codex_agent(
            codex_bin,
            TESTER_PROMPT_PATH,
            tester_output_path,
            "workspace-write",
            attempt,
            "Tester Agent",
            extra_feedback,
        )
        append_agent_message(TESTER_LOG_PATH, tester_output_path)
        append_process_output(TESTER_LOG_PATH, tester_result)
        if tester_result.returncode != 0:
            state["status"] = "failed"
            state["pipeline"]["result"] = "tester_failed"
            write_state(state)
            summarize_results(False, attempt, False, "BLOCKED", [])
            sys.stderr.write(tester_result.stdout)
            sys.stderr.write(tester_result.stderr)
            return tester_result.returncode

        tests_ok, test_results = run_test_commands(attempt)
        final_tests_ok = tests_ok
        final_test_results = test_results

        append_attempt_header(REVIEW_PATH, "Reviewer Agent", attempt)
        reviewer_output_path = WORKSPACE / f".review_attempt_{attempt}.md"
        reviewer_feedback = extra_feedback
        if not tests_ok:
            reviewer_feedback = (reviewer_feedback + "\n\nTests failed. Review with that failure in mind.").strip()
        reviewer_result = run_codex_agent(
            codex_bin,
            REVIEWER_PROMPT_PATH,
            reviewer_output_path,
            "read-only",
            attempt,
            "Reviewer Agent",
            reviewer_feedback,
        )
        append_agent_message(REVIEW_PATH, reviewer_output_path)
        append_process_output(REVIEW_PATH, reviewer_result)
        if reviewer_result.returncode != 0:
            state["status"] = "failed"
            state["pipeline"]["result"] = "reviewer_failed"
            write_state(state)
            summarize_results(False, attempt, tests_ok, "BLOCKED", test_results)
            sys.stderr.write(reviewer_result.stdout)
            sys.stderr.write(reviewer_result.stderr)
            return reviewer_result.returncode

        review_status = parse_review_status()
        final_review_status = review_status
        if tests_ok and review_status == "APPROVED":
            success = True
            state["status"] = "completed"
            state["pipeline"]["result"] = "approved"
            state["pipeline"]["completed_at"] = utc_now()
            write_state(state)
            summarize_results(True, attempt, tests_ok, review_status, test_results)
            print(f"Pipeline completed successfully after attempt {attempt}")
            return 0

        extra_feedback = (
            "Pipeline requires another coder pass.\n\n"
            f"Tests status: {'PASS' if tests_ok else 'FAIL'}\n"
            f"Reviewer status: {review_status}\n\n"
            "Use the latest test report and review findings as the sole rework input."
        )

    state["status"] = "failed"
    state["pipeline"]["result"] = "max_retries_exhausted"
    state["pipeline"]["completed_at"] = utc_now()
    write_state(state)
    summarize_results(success, MAX_RETRIES, final_tests_ok, final_review_status, final_test_results)
    print("Pipeline failed after max retries.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
