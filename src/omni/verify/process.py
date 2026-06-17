"""Verification command execution and preflight orchestration."""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from omni.verify.command_safety import VerifyCommandError, _command_args
from omni.verify.deps import os, signal
from omni.verify.selection import (
    REASON_CODE_UNKNOWN,
    VERIFY_PREDICATE,
    _resolve_predicate,
    _resolve_qualifier,
    _select_verification_command,
)
from omni.verify.inputs import validate_selection_inputs
from omni.verify.text import _safe_output_with_flag

DEFAULT_TIMEOUT_SECONDS = 120
MAX_CAPTURE_BYTES = 64 * 1024
READ_CHUNK_BYTES = 4096
REASON_CODE_PASSED = "passed"
REASON_CODE_FAILED_EXIT_CODE = "failed_exit_code"
REASON_CODE_TIMED_OUT = "timed_out"
REASON_CODE_START_FAILED = "start_failed"


def run_preflight(
    conn,
    root: Path | str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    qualifier: str | None = None,
    task_type: str | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    """Execute the active project test command without writing Cairn Memory state."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    validate_selection_inputs(task_type=task_type, profile=profile)

    root_path = Path(root).resolve()
    predicate = _resolve_predicate(profile)
    effective_qualifier = _resolve_qualifier(qualifier, task_type)
    selection = _select_verification_command(
        conn,
        predicate=predicate,
        qualifier=effective_qualifier,
        task_type=task_type,
        profile=profile,
        explicit_qualifier=qualifier is not None,
    )
    result = _base_result(root_path, timeout_seconds, selection, predicate=predicate)
    if task_type is not None:
        result["task_type"] = task_type
    if profile is not None:
        result["profile"] = profile
    if selection["status"] != "selected":
        result["status"] = "unknown"
        result["reason"] = selection["reason"]
        result["reason_code"] = selection["reason_code"]
        return result

    command = selection["_command_raw"]
    try:
        command_args = _command_args(command, root_path)
    except VerifyCommandError as exc:
        result["status"] = "unknown"
        result["reason"] = str(exc)
        result["reason_code"] = exc.reason_code
        return result

    started = time.perf_counter()
    try:
        from omni import verify as verify_module

        completed = verify_module._run_process(
            command_args,
            root_path,
            timeout_seconds=timeout_seconds,
        )
    except OSError as exc:
        duration_ms = _duration_ms(started)
        stderr_excerpt, stderr_truncated = _safe_output_with_flag(str(exc))
        result.update(
            {
                "status": "failed",
                "reason_code": REASON_CODE_START_FAILED,
                "exit_code": None,
                "duration_ms": duration_ms,
                "stdout_excerpt": "",
                "stderr_excerpt": stderr_excerpt,
                "stdout_truncated": False,
                "stderr_truncated": stderr_truncated,
                "reason": "verification command could not be started",
            }
        )
        return result

    duration_ms = _duration_ms(started)
    timed_out = bool(completed["timed_out"])
    exit_code = completed["exit_code"]
    stdout_excerpt, stdout_text_truncated = _safe_output_with_flag(completed["stdout"])
    stderr_excerpt, stderr_text_truncated = _safe_output_with_flag(completed["stderr"])
    stdout_truncated = stdout_text_truncated or bool(completed["stdout_capture_truncated"])
    stderr_truncated = stderr_text_truncated or bool(completed["stderr_capture_truncated"])
    if timed_out:
        result.update(
            {
                "status": "failed",
                "reason_code": REASON_CODE_TIMED_OUT,
                "exit_code": None,
                "duration_ms": duration_ms,
                "timed_out": True,
                "stdout_excerpt": stdout_excerpt,
                "stderr_excerpt": stderr_excerpt,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
                "reason": f"verification command timed out after {timeout_seconds}s",
            }
        )
        return result

    assert isinstance(exit_code, int)
    result.update(
        {
            "status": "passed" if exit_code == 0 else "failed",
            "reason_code": (
                REASON_CODE_PASSED if exit_code == 0 else REASON_CODE_FAILED_EXIT_CODE
            ),
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "stdout_excerpt": stdout_excerpt,
            "stderr_excerpt": stderr_excerpt,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "reason": (
                "verification command passed"
                if exit_code == 0
                else f"verification command failed with exit code {exit_code}"
            ),
        }
    )
    return result


def _base_result(
    root: Path,
    timeout_seconds: int,
    selection: dict[str, Any],
    *,
    predicate: str = VERIFY_PREDICATE,
) -> dict[str, Any]:
    result = {
        "status": "unknown",
        "reason_code": selection.get("reason_code", REASON_CODE_UNKNOWN),
        "predicate": predicate,
        "qualifier": selection.get("qualifier"),
        "command": selection.get("command"),
        "selection_mode": selection.get("selection_mode", "auto"),
        "selection_reason": selection.get("selection_reason", selection.get("reason", "unknown")),
        "candidate_commands": selection.get("candidate_commands", []),
        "candidate_commands_omitted": selection.get("candidate_commands_omitted", 0),
        "cwd": str(root),
        "exit_code": None,
        "duration_ms": 0,
        "timed_out": False,
        "timeout_seconds": timeout_seconds,
        "stdout_excerpt": "",
        "stderr_excerpt": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "reason": selection.get("reason", "unknown"),
    }
    for key in ("available_qualifiers", "disambiguation_hint"):
        if key in selection:
            result[key] = selection[key]
    return result


def _duration_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _run_process(
    command_args: list[str],
    root_path: Path,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    stdout = bytearray()
    stderr = bytearray()
    stdout_capture_truncated = [False]
    stderr_capture_truncated = [False]
    process = subprocess.Popen(
        command_args,
        cwd=root_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=os.name != "nt",
    )
    threads = [
        threading.Thread(
            target=_read_limited,
            args=(process.stdout, stdout, stdout_capture_truncated),
            daemon=True,
        ),
        threading.Thread(
            target=_read_limited,
            args=(process.stderr, stderr, stderr_capture_truncated),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    timed_out = False
    exit_code: int | None
    try:
        exit_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = None
        _terminate_process_tree(process)
        process.wait()
    except BaseException:
        _terminate_process_tree(process)
        try:
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        raise

    for thread in threads:
        thread.join(timeout=1)

    return {
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout": bytes(stdout),
        "stderr": bytes(stderr),
        "stdout_capture_truncated": stdout_capture_truncated[0],
        "stderr_capture_truncated": stderr_capture_truncated[0],
    }


def _read_limited(stream: Any, buffer: bytearray, truncated: list[bool]) -> None:
    if stream is None:
        return
    try:
        while chunk := stream.read(READ_CHUNK_BYTES):
            remaining = MAX_CAPTURE_BYTES - len(buffer)
            if remaining > 0:
                buffer.extend(chunk[:remaining])
            if len(chunk) > max(remaining, 0):
                truncated[0] = True
    finally:
        stream.close()


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            if process.poll() is not None:
                return
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        if process.poll() is not None:
            return
    try:
        process.kill()
    except OSError:
        pass
