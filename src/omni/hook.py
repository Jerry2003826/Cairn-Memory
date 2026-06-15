"""Claude Code hook capture entrypoints."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from omni.capture import InstallResult, default as default_capture_engine
from omni.capture.claude import install_claude_hooks
from omni.config import project_root
from omni.redact import RedactionResult, is_skiplisted_path, redact, redact_minimal

MAX_HOOK_EVENT_PARSE_BYTES = 256 * 1024
COMMAND_KEYS = {"command", "cmd"}
INPUT_CONTAINER_KEYS = {"tool_input", "input", "parameters", "args"}
INPUT_CONTENT_KEYS = {"content", "new_string", "old_string", "text", "data"}
RESPONSE_CONTAINER_KEYS = {"tool_response", "tool_result", "response", "result"}
SHELL_CONTROL_TOKENS = {"|", "||", "&&", ";", "&", "("}
SHELL_WRITE_REDIRECT_TOKENS = {">", ">>", ">|", "&>", "&>>"}

@dataclass(frozen=True)
class HookCaptureResult:
    ok: bool
    spool_path: Path | None = None


def capture_hook(payload: bytes, root: Path | str | None = None) -> HookCaptureResult:
    started = time.perf_counter()
    spool_dir: Path | None = None
    try:
        base = _hook_base(root)
        spool_dir = base / ".omni" / "spool"
        spool_dir.mkdir(parents=True, exist_ok=True)
        redaction = _redact_payload(payload)
        event = _event_for_enqueue(payload)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        record = {
            "meta": {
                "elapsed_ms": elapsed_ms,
                "redaction_status": redaction.status,
                "detectors": list(redaction.detectors),
            },
            "payload": redaction.data.decode("utf-8", errors="replace"),
        }
        line = json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        spool_path = spool_dir / f"hook-{time.time_ns()}-{uuid.uuid4().hex}.jsonl"
        temp_path = spool_path.with_suffix(".jsonl.tmp")
        temp_path.write_bytes(line + b"\n")
        temp_path.replace(spool_path)

        if event.get("hook_event_name") in default_capture_engine().ingest_events:
            _enqueue_ingest_request(spool_dir, event)

        return HookCaptureResult(ok=True, spool_path=spool_path)
    except Exception as exc:
        if spool_dir is not None:
            _write_error(spool_dir, exc)
        return HookCaptureResult(ok=True)


def run_from_stdin() -> HookCaptureResult:
    try:
        payload = sys.stdin.buffer.read()
    except Exception:
        payload = b""
    try:
        return capture_hook(payload)
    except Exception:
        return HookCaptureResult(ok=True)


def main() -> int:
    run_from_stdin()
    return 0


def _redact_payload(payload: bytes) -> RedactionResult:
    skiplisted = _redact_skiplisted_payload(payload)
    if skiplisted is not None:
        return skiplisted
    try:
        return redact_minimal(payload)
    except Exception:
        return RedactionResult(
            data=_redaction_failed_stub(payload),
            status="withheld",
            detectors=("withheld",),
        )


def _redaction_failed_stub(payload: bytes) -> bytes:
    stub = {
        "error": "redaction_failed",
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "byte_len": len(payload),
    }
    return json.dumps(stub, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _skiplisted_payload_stub(payload: bytes) -> bytes:
    stub = {
        "error": "skiplisted_path_withheld",
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "byte_len": len(payload),
    }
    return json.dumps(stub, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _event_from_payload(payload: bytes) -> dict[str, object]:
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _event_for_enqueue(payload: bytes) -> dict[str, object]:
    ingest_events = default_capture_engine().ingest_events
    if len(payload) > MAX_HOOK_EVENT_PARSE_BYTES:
        if not _payload_may_contain_ingest_event(payload, ingest_events):
            return {}
        event = _top_level_json_string_fields(
            payload,
            {"hook_event_name", "session_id", "transcript_path"},
        )
        return event if event.get("hook_event_name") in ingest_events else {}
    return _event_from_payload(payload)


def _payload_may_contain_ingest_event(payload: bytes, ingest_events: frozenset[str]) -> bool:
    return any(f'"{name}"'.encode() in payload for name in ingest_events)


def _top_level_json_string_fields(payload: bytes, keys: set[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    depth = 0
    index = 0
    while index < len(payload):
        char = payload[index]
        if char == ord('"'):
            raw_key, next_index = _read_json_string(payload, index)
            if raw_key is None:
                return fields
            if depth == 1:
                colon = _skip_json_whitespace(payload, next_index)
                if colon < len(payload) and payload[colon] == ord(":"):
                    key = _decode_json_string(raw_key)
                    value_start = _skip_json_whitespace(payload, colon + 1)
                    if (
                        key in keys
                        and value_start < len(payload)
                        and payload[value_start] == ord('"')
                    ):
                        raw_value, value_end = _read_json_string(payload, value_start)
                        if raw_value is None:
                            return fields
                        value = _decode_json_string(raw_value)
                        if value is not None:
                            fields[key] = value
                            if len(fields) == len(keys):
                                return fields
                        index = value_end
                        continue
            index = next_index
            continue
        if char == ord("{"):
            depth += 1
        elif char == ord("}"):
            depth -= 1
            if depth < 0:
                return fields
        index += 1
    return fields


def _read_json_string(payload: bytes, start: int) -> tuple[bytes | None, int]:
    escaped = False
    index = start + 1
    while index < len(payload):
        char = payload[index]
        if escaped:
            escaped = False
        elif char == ord("\\"):
            escaped = True
        elif char == ord('"'):
            return payload[start + 1 : index], index + 1
        index += 1
    return None, len(payload)


def _decode_json_string(raw: bytes) -> str | None:
    try:
        value = json.loads(b'"' + raw + b'"')
    except Exception:
        return None
    return value if isinstance(value, str) else None


def _skip_json_whitespace(payload: bytes, index: int) -> int:
    while index < len(payload) and payload[index] in b" \t\r\n":
        index += 1
    return index


def _redact_line(record: dict[str, object]) -> bytes:
    encoded = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return redact(encoded).data


def _hook_base(root: Path | str | None) -> Path:
    configured = root or os.environ.get("CLAUDE_PROJECT_DIR")
    if configured is not None:
        return Path(configured).resolve()
    return project_root()


def _redact_skiplisted_payload(payload: bytes) -> RedactionResult | None:
    if len(payload) > MAX_HOOK_EVENT_PARSE_BYTES:
        if _raw_payload_references_skiplisted_path(payload):
            return RedactionResult(
                data=_skiplisted_payload_stub(payload),
                status="withheld",
                detectors=("skiplist",),
            )
        return None
    event = _event_from_payload(payload)
    if not event:
        return None
    if not _event_input_references_skiplisted_path(event):
        return None

    sanitized = _withhold_skiplisted_content(event, _skiplisted_payload_stub(payload))
    encoded = json.dumps(
        sanitized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    redaction = redact_minimal(encoded)
    return RedactionResult(
        data=redaction.data,
        status="withheld",
        detectors=tuple(dict.fromkeys(("skiplist", *redaction.detectors))),
    )


def _event_input_references_skiplisted_path(event: dict[str, object]) -> bool:
    for key in ("tool_input", "input", "parameters", "args"):
        value = event.get(key)
        if _input_value_references_skiplisted_path(value):
            return True
    return False


def _input_value_references_skiplisted_path(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"file_path", "filepath", "path", "filename"}:
                if _string_references_skiplisted_path(str(item)):
                    return True
            if lowered in COMMAND_KEYS and isinstance(item, str):
                if _command_references_skiplisted_path(item):
                    return True
            if isinstance(item, (dict, list)) and _input_value_references_skiplisted_path(item):
                return True
    elif isinstance(value, list):
        return any(_input_value_references_skiplisted_path(item) for item in value)
    return False


def _raw_payload_references_skiplisted_path(payload: bytes) -> bool:
    pattern = re.compile(
        rb'"(file_path|filepath|path|filename|command|cmd)"\s*:\s*"((?:\\.|[^"\\])*)"'
    )
    for match in pattern.finditer(payload):
        key = match.group(1).decode("ascii", errors="ignore").lower()
        value = _decode_json_string(match.group(2))
        if value is None:
            continue
        if key in COMMAND_KEYS:
            if _command_references_skiplisted_path(value):
                return True
        elif _string_references_skiplisted_path(value):
            return True
    return False


def _string_references_skiplisted_path(value: str) -> bool:
    for token in re.split(r"[\s\"'`=,:;|&<>\[\]{}()]+", value):
        if not token:
            continue
        name = token.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
        if name and is_skiplisted_path(name):
            return True
    return False


def _command_references_skiplisted_path(command: str) -> bool:
    for token in re.split(r"[\s\"'`=,:;|&<>\[\]{}()]+", command):
        if "/" not in token and "\\" not in token and not token.startswith("."):
            continue
        if _string_references_skiplisted_path(token):
            return True
    return False


def _command_writes_skiplisted_path(command: str) -> bool:
    tokens = _shell_tokens(command)
    for index, token in enumerate(tokens[:-1]):
        if token in SHELL_WRITE_REDIRECT_TOKENS:
            if _string_references_skiplisted_path(tokens[index + 1]):
                return True
    for index, token in enumerate(tokens):
        if token != "tee":
            continue
        if index != 0 and tokens[index - 1] not in SHELL_CONTROL_TOKENS:
            continue
        if _tee_writes_skiplisted_path(tokens[index + 1 :]):
            return True
    return False


def _shell_tokens(command: str) -> list[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return []


def _tee_writes_skiplisted_path(tokens: list[str]) -> bool:
    for token in tokens:
        if token in SHELL_CONTROL_TOKENS or token in SHELL_WRITE_REDIRECT_TOKENS:
            return False
        if token == "--" or token.startswith("-"):
            continue
        if _string_references_skiplisted_path(token):
            return True
    return False


def _withhold_skiplisted_content(value: object, stub: bytes) -> object:
    stub_obj = json.loads(stub.decode("utf-8"))
    return _replace_skiplisted_content(
        value,
        stub_obj,
        in_response=False,
        in_input=False,
    )


def _replace_skiplisted_content(
    value: object,
    stub: dict[str, object],
    *,
    in_response: bool,
    in_input: bool,
) -> object:
    if isinstance(value, dict):
        replaced: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            key_in_response = in_response or key_text in RESPONSE_CONTAINER_KEYS
            key_in_input = in_input or key_lower in INPUT_CONTAINER_KEYS
            if key_in_response and isinstance(item, str):
                replaced[key] = stub
            elif key_in_input and key_lower in INPUT_CONTENT_KEYS:
                replaced[key] = stub
            elif (
                key_in_input
                and key_lower in COMMAND_KEYS
                and isinstance(item, str)
                and _command_writes_skiplisted_path(item)
            ):
                replaced[key] = stub
            else:
                replaced[key] = _replace_skiplisted_content(
                    item,
                    stub,
                    in_response=key_in_response,
                    in_input=key_in_input,
                )
        return replaced
    if isinstance(value, list):
        return [
            _replace_skiplisted_content(
                item,
                stub,
                in_response=in_response,
                in_input=in_input,
            )
            for item in value
        ]
    return stub if in_response and isinstance(value, str) else value


def _enqueue_ingest_request(spool_dir: Path, event: dict[str, object]) -> None:
    request = {
        "event": event.get("hook_event_name"),
        "session_id": event.get("session_id"),
        "transcript_path": event.get("transcript_path"),
    }
    line = _redact_line(request)
    target = spool_dir / f"ingest-{time.time_ns()}-{uuid.uuid4().hex}.json"
    temp = target.with_suffix(".json.tmp")
    temp.write_bytes(line + b"\n")
    temp.replace(target)


def _write_error(spool_dir: Path, exc: Exception) -> None:
    try:
        spool_dir.mkdir(parents=True, exist_ok=True)
        error = {
            "error": type(exc).__name__,
            "message": str(exc),
        }
        line = _redact_line(error)
        with (spool_dir / "_errors.log").open("ab") as handle:
            handle.write(line + b"\n")
    except Exception:
        pass
