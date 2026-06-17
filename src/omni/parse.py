"""Tolerant transcript JSONL parser."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from omni._common import (
    is_redaction_placeholder as _is_redaction_placeholder,
    merge_redaction_status as _merge_redaction_status,
    optional_int as _optional_int,
)
from omni.redact import redact

KNOWN_EVENT_KEYS = {
    "created_at",
    "duration_ms",
    "event_type",
    "exit_code",
    "hook_event_name",
    "id",
    "name",
    "timestamp",
    "tool",
    "tool_name",
    "tool_use_id",
    "ts",
    "type",
}

MAX_TRANSCRIPT_ARCHIVE_BYTES = 768 * 1024


@dataclass(frozen=True)
class NormalizedEvent:
    seq: int
    ts: str
    event_type: str
    tool: str | None
    tool_use_id: str | None
    exit_code: int | None
    duration_ms: int | None
    source: str
    meta: dict[str, Any]
    redaction_status: str = "clean"
    detectors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "detectors": list(self.detectors),
            "duration_ms": self.duration_ms,
            "event_type": self.event_type,
            "exit_code": self.exit_code,
            "meta": self.meta,
            "redaction_status": self.redaction_status,
            "seq": self.seq,
            "source": self.source,
            "tool": self.tool,
            "tool_use_id": self.tool_use_id,
            "ts": self.ts,
        }


@dataclass(frozen=True)
class TranscriptArchive:
    kind: str
    payload: bytes
    line_count: int
    redaction_status: str
    detectors: tuple[str, ...]


@dataclass(frozen=True)
class ParseResult:
    events: list[NormalizedEvent]
    archive: TranscriptArchive | None


@dataclass
class _TranscriptArchiveAccumulator:
    lines: list[bytes] = field(default_factory=list)
    line_count: int = 0
    payload_bytes: int = 0
    omitted_lines: int = 0
    detectors: list[str] = field(default_factory=list)
    status: str = "clean"

    def append_bad_line(self, line_no: int, reason: str, raw_line: bytes) -> None:
        record, status, detectors = _archive_record(line_no, reason, raw_line)
        self.line_count += 1
        self.payload_bytes, self.omitted_lines = _append_archive_record(
            self.lines,
            self.payload_bytes,
            self.omitted_lines,
            record,
        )
        self.status = _merge_redaction_status(self.status, status)
        self.detectors.extend(detectors)

    def build(self) -> TranscriptArchive | None:
        if not self.line_count:
            return None
        if self.omitted_lines:
            self.status = _merge_redaction_status(self.status, "truncated")
            _append_archive_truncation_record(
                self.lines,
                self.payload_bytes,
                self.omitted_lines,
            )
        archive_payload = b"\n".join(self.lines) + b"\n"
        return TranscriptArchive(
            kind="transcript_archive",
            payload=archive_payload,
            line_count=self.line_count,
            redaction_status=self.status,
            detectors=tuple(dict.fromkeys(self.detectors)),
        )


@dataclass(frozen=True)
class _LineOutcome:
    events: list[NormalizedEvent]
    archive_reason: str | None = None


def parse_transcript(
    path: Path | str,
    *,
    engine: str = "claude",
) -> ParseResult:
    transcript_path = Path(path)
    events: list[NormalizedEvent] = []
    archive = _TranscriptArchiveAccumulator()

    with transcript_path.open("rb") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            raw_line = raw_line.rstrip(b"\r\n")
            if not raw_line.strip():
                continue
            try:
                parsed = json.loads(raw_line.decode("utf-8"))
            except Exception:
                archive.append_bad_line(line_no, "invalid_json", raw_line)
                continue

            if not isinstance(parsed, dict) or not _event_type(parsed):
                archive.append_bad_line(line_no, _unknown_shape_reason(engine), raw_line)
                continue

            outcome = _normalize_event(len(events) + 1, parsed, engine=engine)
            if outcome.archive_reason is not None:
                archive.append_bad_line(line_no, outcome.archive_reason, raw_line)
                continue
            events.extend(outcome.events)

    return ParseResult(events=events, archive=archive.build())


def events_as_jsonl(events: list[NormalizedEvent]) -> str:
    lines: list[str] = []
    for event in events:
        raw = json.dumps(
            event.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        line = redact(raw).data.decode("utf-8", errors="replace")
        lines.append(line if line.endswith("\n") else line + "\n")
    return "".join(lines)


def _normalize_event(
    seq: int,
    row: dict[str, Any],
    *,
    engine: str,
) -> _LineOutcome:
    if engine == "opencode":
        event = _normalize_opencode_tool_use(seq, row)
        if event is None:
            return _LineOutcome([], archive_reason=_unknown_shape_reason(engine))
        return _LineOutcome([event])
    if engine == "qwen":
        events = _normalize_qwen_tool_events(seq, row)
        if events is None:
            return _LineOutcome([], archive_reason=_unknown_shape_reason(engine))
        return _LineOutcome(events)

    return _LineOutcome([_normalize_generic_event(seq, row)])


def _normalize_generic_event(seq: int, row: dict[str, Any]) -> NormalizedEvent:
    meta = {key: value for key, value in row.items() if key not in KNOWN_EVENT_KEYS}
    return _make_normalized_event(
        seq,
        row,
        event_type=_event_type(row),
        tool=row.get("tool") or row.get("tool_name") or row.get("name"),
        tool_use_id=row.get("tool_use_id") or row.get("id"),
        exit_code=row.get("exit_code"),
        duration_ms=row.get("duration_ms"),
        meta=meta,
    )


def _normalize_opencode_tool_use(seq: int, row: dict[str, Any]) -> NormalizedEvent | None:
    if row.get("type") != "tool_use":
        return None
    part = row.get("part")
    if not isinstance(part, dict):
        return None
    if part.get("type") != "tool":
        return None
    if not isinstance(part.get("tool"), str) or not part.get("tool"):
        return None
    if not isinstance(part.get("callID"), str) or not part.get("callID"):
        return None
    state = part.get("state")
    if not isinstance(state, dict):
        return None

    state_input = state.get("input")
    metadata = state.get("metadata")
    if state_input is not None and not isinstance(state_input, dict):
        return None
    if metadata is not None and not isinstance(metadata, dict):
        return None
    if not isinstance(state_input, dict) and not isinstance(metadata, dict):
        return None
    if metadata is None:
        metadata = {}
    time = state.get("time")
    if not isinstance(time, dict):
        time = {}

    meta = {key: value for key, value in row.items() if key not in KNOWN_EVENT_KEYS}
    return _make_normalized_event(
        seq,
        row,
        event_type=row.get("type"),
        tool=part.get("tool"),
        tool_use_id=part.get("callID"),
        exit_code=_optional_int(metadata.get("exit")),
        duration_ms=_duration_ms(time.get("start"), time.get("end")),
        meta=meta,
        meta_transform=_opencode_meta_transform,
    )


def _normalize_qwen_tool_events(seq: int, row: dict[str, Any]) -> list[NormalizedEvent] | None:
    event_type = row.get("type")
    if event_type == "assistant":
        return _normalize_qwen_assistant_tool_uses(seq, row)
    if event_type == "user":
        return _normalize_qwen_user_tool_results(seq, row)
    if event_type == "tool_use":
        return _normalize_qwen_direct_tool_use(seq, row)
    if event_type in {"result", "system", "stream_event"}:
        return []
    return None


def _normalize_qwen_assistant_tool_uses(
    seq: int,
    row: dict[str, Any],
) -> list[NormalizedEvent]:
    events: list[NormalizedEvent] = []
    for index, block in enumerate(_qwen_message_content(row)):
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        tool = block.get("name")
        tool_use_id = block.get("id")
        if not isinstance(tool, str) or not tool:
            continue
        if not isinstance(tool_use_id, str) or not tool_use_id:
            continue
        event = _make_normalized_event(
            seq + len(events),
            row,
            event_type="tool_use",
            tool=tool,
            tool_use_id=tool_use_id,
            meta=_qwen_block_meta(row, block, index=index),
        )
        events.append(event)
    return events


def _normalize_qwen_user_tool_results(
    seq: int,
    row: dict[str, Any],
) -> list[NormalizedEvent]:
    events: list[NormalizedEvent] = []
    for index, block in enumerate(_qwen_message_content(row)):
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        tool_use_id = block.get("tool_use_id")
        if not isinstance(tool_use_id, str) or not tool_use_id:
            continue
        event = _make_normalized_event(
            seq + len(events),
            row,
            event_type="tool_result",
            tool=None,
            tool_use_id=tool_use_id,
            meta=_qwen_block_meta(row, block, index=index),
        )
        events.append(event)
    return events


def _normalize_qwen_direct_tool_use(
    seq: int,
    row: dict[str, Any],
) -> list[NormalizedEvent] | None:
    tool = row.get("name") or row.get("tool") or row.get("tool_name")
    tool_use_id = row.get("tool_use_id") or row.get("id")
    if not isinstance(tool, str) or not tool:
        return None
    if not isinstance(tool_use_id, str) or not tool_use_id:
        return None
    meta = {key: value for key, value in row.items() if key not in KNOWN_EVENT_KEYS}
    return [
        _make_normalized_event(
            seq,
            row,
            event_type="tool_use",
            tool=tool,
            tool_use_id=tool_use_id,
            meta=meta,
        )
    ]


def _qwen_message_content(row: dict[str, Any]) -> list[Any]:
    message = row.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, list):
        return content
    return []


def _qwen_block_meta(
    row: dict[str, Any],
    block: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    meta = {key: value for key, value in row.items() if key not in KNOWN_EVENT_KEYS}
    meta["qwen_content_index"] = index
    meta["qwen_content_block"] = block
    input_payload = block.get("input")
    if isinstance(input_payload, dict):
        meta["input"] = input_payload
    return meta


def _make_normalized_event(
    seq: int,
    row: dict[str, Any],
    *,
    event_type: Any,
    tool: Any,
    tool_use_id: Any,
    exit_code: Any = None,
    duration_ms: Any = None,
    meta: dict[str, Any],
    meta_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> NormalizedEvent:
    ts, ts_status, ts_detectors = _redacted_str(
        row.get("timestamp") or row.get("ts") or row.get("created_at") or ""
    )
    redacted_event_type, event_status, event_detectors = _redacted_str(event_type)
    redacted_tool, tool_status, tool_detectors = _redacted_optional_str(tool)
    redacted_tool_use_id, tool_id_status, tool_id_detectors = _redacted_optional_str(
        tool_use_id
    )
    redacted_meta, meta_status, meta_detectors = _redacted_meta(meta)
    if meta_transform is not None:
        redacted_meta = meta_transform(redacted_meta)
    return NormalizedEvent(
        seq=seq,
        ts=ts,
        event_type=redacted_event_type,
        tool=redacted_tool,
        tool_use_id=redacted_tool_use_id,
        exit_code=_optional_int(exit_code),
        duration_ms=_optional_int(duration_ms),
        source="transcript",
        meta=redacted_meta,
        redaction_status=_merge_redaction_status(
            ts_status,
            event_status,
            tool_status,
            tool_id_status,
            meta_status,
        ),
        detectors=tuple(
            dict.fromkeys(
                ts_detectors
                + event_detectors
                + tool_detectors
                + tool_id_detectors
                + meta_detectors
            )
        ),
    )


def _opencode_meta_transform(redacted_meta: dict[str, Any]) -> dict[str, Any]:
    redacted_state = redacted_meta.get("part", {}).get("state", {})
    redacted_input = (
        redacted_state.get("input") if isinstance(redacted_state, dict) else None
    )
    if isinstance(redacted_input, dict):
        original_input = redacted_meta.get("input")
        if original_input is not None and original_input != redacted_input:
            redacted_meta["opencode_raw_input"] = original_input
        redacted_meta["input"] = redacted_input
    return redacted_meta


def _duration_ms(start: Any, end: Any) -> int | None:
    start_ms = _optional_int(start)
    end_ms = _optional_int(end)
    if start_ms is None or end_ms is None:
        return None
    return max(0, end_ms - start_ms)


def _redacted_meta(meta: dict[str, Any]) -> tuple[dict[str, Any], str, tuple[str, ...]]:
    if not meta:
        return {}, "clean", ()
    encoded = json.dumps(
        meta,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    redaction = redact(encoded)
    redacted = redaction.data.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(redacted)
    except json.JSONDecodeError:
        return {"redacted_meta": redacted}, redaction.status, redaction.detectors
    result = parsed if isinstance(parsed, dict) else {"redacted_meta": redacted}
    return result, redaction.status, redaction.detectors


def _redacted_str(value: Any) -> tuple[str, str, tuple[str, ...]]:
    text = str(value)
    if _is_redaction_placeholder(text):
        return text, "redacted", ()
    redaction = redact(text.encode("utf-8"))
    return redaction.data.decode("utf-8", errors="replace"), redaction.status, redaction.detectors


def _redacted_optional_str(value: Any) -> tuple[str | None, str, tuple[str, ...]]:
    if value is None:
        return None, "clean", ()
    return _redacted_str(value)


def _event_type(row: dict[str, Any]) -> Any:
    return row.get("type") or row.get("event_type") or row.get("hook_event_name")


def _unknown_shape_reason(engine: str) -> str:
    if engine == "opencode":
        return "unknown_opencode_shape"
    if engine == "qwen":
        return "unknown_qwen_shape"
    return "unknown_transcript_shape"


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _archive_record(
    line_no: int, reason: str, raw_line: bytes
) -> tuple[bytes, str, tuple[str, ...]]:
    redaction = redact(raw_line)
    record = {
        "detectors": list(redaction.detectors),
        "line": line_no,
        "payload": redaction.data.decode("utf-8", errors="replace"),
        "reason": reason,
        "redaction_status": redaction.status,
    }
    encoded = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return redact(encoded).data, redaction.status, redaction.detectors


def _append_archive_record(
    archive_lines: list[bytes],
    archive_payload_bytes: int,
    archive_omitted_lines: int,
    record: bytes,
) -> tuple[int, int]:
    if archive_omitted_lines:
        return archive_payload_bytes, archive_omitted_lines + 1
    record_size = len(record) + 1
    if archive_payload_bytes + record_size <= MAX_TRANSCRIPT_ARCHIVE_BYTES:
        archive_lines.append(record)
        return archive_payload_bytes + record_size, archive_omitted_lines
    return archive_payload_bytes, 1


def _append_archive_truncation_record(
    archive_lines: list[bytes],
    archive_payload_bytes: int,
    archive_omitted_lines: int,
) -> None:
    omitted_lines = archive_omitted_lines
    while archive_lines:
        truncated = _archive_truncation_record(omitted_lines)
        if archive_payload_bytes + len(truncated) + 1 <= MAX_TRANSCRIPT_ARCHIVE_BYTES:
            archive_lines.append(truncated)
            return
        removed = archive_lines.pop()
        archive_payload_bytes -= len(removed) + 1
        omitted_lines += 1
    archive_lines.append(_archive_truncation_record(omitted_lines))


def _archive_truncation_record(omitted_lines: int) -> bytes:
    return json.dumps(
        {
            "error": "archive_truncated",
            "omitted_lines": omitted_lines,
            "redaction_status": "truncated",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
