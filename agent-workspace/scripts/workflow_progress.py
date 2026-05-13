from __future__ import annotations

import json
import os
import re
import selectors
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


HEARTBEAT_INTERVAL_SECONDS = 30
DEFAULT_MAX_PROGRESS_LOG_BYTES = 1_000_000
DEFAULT_MAX_TERMINAL_OUTPUT_CHARS = 60_000
DEFAULT_MAX_CAPTURED_OUTPUT_CHARS = 160_000
DEFAULT_MAX_PROGRESS_MESSAGE_CHARS = 8_000

SECRET_PATTERNS = [
    re.compile(r'("?(?:password|wifi_password|device_token|plantlab_token|claim_token|token|x-device-token)"?\s*[:=]\s*")([^"]+)(")', re.IGNORECASE),
    re.compile(r"((?:password|wifi_password|device_token|plantlab_token|claim_token|token|x-device-token)\s*[:=]\s*)([^\s,;]+)", re.IGNORECASE),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def local_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        if pattern.groups == 3:
            redacted = pattern.sub(r"\1<redacted>\3", redacted)
        else:
            redacted = pattern.sub(r"\1<redacted>", redacted)
    return redacted


def _env_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return max(1, int(raw_value.strip()))
    except ValueError:
        return default


def _max_progress_log_bytes() -> int:
    return _env_int("CODEX_WORKFLOW_MAX_PROGRESS_LOG_BYTES", DEFAULT_MAX_PROGRESS_LOG_BYTES)


def _max_terminal_output_chars() -> int:
    return _env_int("CODEX_WORKFLOW_MAX_TERMINAL_OUTPUT_CHARS", DEFAULT_MAX_TERMINAL_OUTPUT_CHARS)


def _max_captured_output_chars() -> int:
    return _env_int("CODEX_WORKFLOW_MAX_CAPTURED_OUTPUT_CHARS", DEFAULT_MAX_CAPTURED_OUTPUT_CHARS)


def _max_progress_message_chars() -> int:
    return _env_int("CODEX_WORKFLOW_MAX_PROGRESS_MESSAGE_CHARS", DEFAULT_MAX_PROGRESS_MESSAGE_CHARS)


def _cap_text(text: str, max_chars: int, *, label: str) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return text[:max_chars] + f"\n[{label} truncated {omitted} chars]\n"


def _append_capped(parts: list[str], text: str, max_chars: int) -> None:
    current = sum(len(part) for part in parts)
    if current >= max_chars:
        return
    remaining = max_chars - current
    if len(text) <= remaining:
        parts.append(text)
    else:
        parts.append(text[:remaining] + f"\n[captured output truncated {len(text) - remaining} chars]\n")


def _cap_progress_log(progress_path: Path) -> None:
    max_bytes = _max_progress_log_bytes()
    if not progress_path.exists():
        return
    try:
        size = progress_path.stat().st_size
    except OSError:
        return
    if size <= max_bytes:
        return

    keep_bytes = max(max_bytes // 2, 1)
    try:
        with progress_path.open("rb") as handle:
            handle.seek(max(0, size - keep_bytes))
            tail = handle.read()
        marker = (
            f"[{local_timestamp()}] [orchestrator] progress.log capped; "
            f"removed approximately {size - keep_bytes} bytes\n"
        ).encode("utf-8")
        progress_path.write_bytes(marker + tail)
    except OSError:
        return


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_progress(output_dir: Path, agent: str, message: str) -> None:
    progress_path = output_dir / "progress.log"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    safe_message = redact_secrets(message.rstrip())
    safe_message = _cap_text(safe_message, _max_progress_message_chars(), label="progress message")
    _cap_progress_log(progress_path)
    with progress_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{local_timestamp()}] [{agent}] {safe_message}\n")


def write_heartbeat(
    output_dir: Path,
    task_id: str,
    agent: str,
    stage: str,
    status: str,
    message: str,
) -> None:
    payload = {
        "task_id": task_id,
        "agent": agent,
        "stage": stage,
        "status": status,
        "last_update": utc_now(),
        "message": redact_secrets(message),
    }
    write_text(output_dir / "heartbeat.json", json.dumps(payload, indent=2) + "\n")


def update_stage(output_dir: Path, stage: str) -> None:
    write_text(output_dir / "current_stage.txt", redact_secrets(stage).strip() + "\n")


def ensure_monitoring_files(output_dir: Path, task_id: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir / "progress.log"
    if not progress_path.exists():
        write_text(progress_path, "")
    heartbeat_path = output_dir / "heartbeat.json"
    if not heartbeat_path.exists():
        write_heartbeat(output_dir, task_id, "orchestrator", "idle", "completed", "idle")
    stage_path = output_dir / "current_stage.txt"
    if not stage_path.exists():
        update_stage(output_dir, "idle")


def mark_stage(output_dir: Path, task_id: str, agent: str, stage: str, message: str) -> None:
    update_stage(output_dir, stage)
    write_heartbeat(output_dir, task_id, agent, stage, "running", message)
    append_progress(output_dir, agent, message)
    print(f"[{agent}] {message}")


def _feed_stdin(process: subprocess.Popen[bytes], data: str) -> None:
    if process.stdin is None:
        return
    try:
        process.stdin.write(data.encode("utf-8"))
        process.stdin.close()
    except BrokenPipeError:
        pass


def run_streaming_process(
    cmd: list[str],
    *,
    input_text: str | None,
    cwd: Path,
    timeout_seconds: int,
    output_dir: Path,
    task_id: str,
    agent: str,
    stage: str,
) -> tuple[subprocess.CompletedProcess[str], bool]:
    """Run a subprocess while streaming output and writing heartbeat/progress files."""
    append_progress(output_dir, agent, f"starting command: {' '.join(cmd)}")
    update_stage(output_dir, stage)
    write_heartbeat(output_dir, task_id, agent, stage, "running", f"{stage} started")

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        start_new_session=True,
    )
    if input_text is not None:
        feeder = threading.Thread(target=_feed_stdin, args=(process, input_text), daemon=True)
        feeder.start()

    selector = selectors.DefaultSelector()
    if process.stdout is not None:
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    if process.stderr is not None:
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    started = time.monotonic()
    last_heartbeat = started
    timed_out = False
    terminal_output_chars = 0
    terminal_output_truncated = False
    max_terminal_chars = _max_terminal_output_chars()
    max_captured_chars = _max_captured_output_chars()

    def write_terminal(text: str, *, stream_name: str) -> None:
        nonlocal terminal_output_chars, terminal_output_truncated
        if terminal_output_chars >= max_terminal_chars:
            if not terminal_output_truncated:
                notice = (
                    f"\n[{agent}] subprocess output exceeded {max_terminal_chars} chars; "
                    "terminal display is truncated. See capped progress.log for recent output.\n"
                )
                sys.stderr.write(notice)
                sys.stderr.flush()
                append_progress(output_dir, agent, "terminal display truncated for large subprocess output")
                terminal_output_truncated = True
            return

        remaining = max_terminal_chars - terminal_output_chars
        visible = text[:remaining]
        terminal_output_chars += len(visible)
        if stream_name == "stdout":
            sys.stdout.write(visible)
            sys.stdout.flush()
        else:
            sys.stderr.write(visible)
            sys.stderr.flush()
        if len(text) > remaining and not terminal_output_truncated:
            notice = (
                f"\n[{agent}] subprocess output exceeded {max_terminal_chars} chars; "
                "terminal display is truncated. See capped progress.log for recent output.\n"
            )
            sys.stderr.write(notice)
            sys.stderr.flush()
            append_progress(output_dir, agent, "terminal display truncated for large subprocess output")
            terminal_output_truncated = True

    while selector.get_map() or process.poll() is None:
        now = time.monotonic()
        if now - started > timeout_seconds:
            timed_out = True
            append_progress(output_dir, agent, f"timeout after {timeout_seconds} seconds; terminating process")
            write_heartbeat(output_dir, task_id, agent, stage, "failed", f"timeout after {timeout_seconds} seconds")
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            break

        if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
            current_stage = (output_dir / "current_stage.txt").read_text(encoding="utf-8").strip()
            message = f"still running; current stage: {current_stage or stage}"
            print(f"[{agent}] {message}")
            append_progress(output_dir, agent, message)
            write_heartbeat(output_dir, task_id, agent, current_stage or stage, "running", message)
            last_heartbeat = now

        for key, _ in selector.select(timeout=1):
            stream = key.fileobj
            chunk = stream.readline()
            if not chunk:
                try:
                    selector.unregister(stream)
                except KeyError:
                    pass
                continue
            text = chunk.decode("utf-8", errors="replace")
            safe_text = redact_secrets(text)
            if key.data == "stdout":
                _append_capped(stdout_parts, safe_text, max_captured_chars)
                write_terminal(safe_text, stream_name="stdout")
                append_progress(output_dir, f"{agent}:stdout", safe_text)
            else:
                _append_capped(stderr_parts, safe_text, max_captured_chars)
                write_terminal(safe_text, stream_name="stderr")
                append_progress(output_dir, f"{agent}:stderr", safe_text)

    if timed_out:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()

    for stream_name, stream in [("stdout", process.stdout), ("stderr", process.stderr)]:
        if stream is None:
            continue
        remaining = stream.read() or b""
        if remaining:
            text = redact_secrets(remaining.decode("utf-8", errors="replace"))
            if stream_name == "stdout":
                _append_capped(stdout_parts, text, max_captured_chars)
                write_terminal(text, stream_name="stdout")
                append_progress(output_dir, f"{agent}:stdout", text)
            else:
                _append_capped(stderr_parts, text, max_captured_chars)
                write_terminal(text, stream_name="stderr")
                append_progress(output_dir, f"{agent}:stderr", text)

    returncode = process.returncode if process.returncode is not None else -1
    status = "completed" if returncode == 0 and not timed_out else "failed"
    write_heartbeat(output_dir, task_id, agent, stage, status, f"{stage} {status}")
    append_progress(output_dir, agent, f"{stage} {status} with returncode={returncode}")
    return subprocess.CompletedProcess(cmd, returncode, "".join(stdout_parts), "".join(stderr_parts)), timed_out
