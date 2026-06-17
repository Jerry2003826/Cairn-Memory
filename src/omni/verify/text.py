"""Redaction-safe text helpers for verify output."""

from __future__ import annotations

from omni._common import truncate_with_suffix
from omni.jsonio import dump_json
from omni.redact import redact

MAX_COMMAND_CHARS = 300
MAX_OUTPUT_CHARS = 4000


def as_json(value: dict) -> str:
    return dump_json(
        value,
        string_sanitizer=lambda s: redact_and_truncate_text(s, MAX_OUTPUT_CHARS),
    )


def _safe_output_with_flag(value: str | bytes) -> tuple[str, bool]:
    return redact_and_truncate_text_with_flag(_to_text(value), MAX_OUTPUT_CHARS)


def redact_and_truncate_text(value: str, max_chars: int) -> str:
    return redact_and_truncate_text_with_flag(value, max_chars)[0]


def redact_and_truncate_text_with_flag(value: str, max_chars: int) -> tuple[str, bool]:
    redacted = redact(value.encode("utf-8", errors="replace")).data.decode(
        "utf-8", errors="replace"
    )
    normalized = redacted.replace("\r\n", "\n").replace("\r", "\n").strip()
    return truncate_with_suffix(normalized, max_chars)


def _sanitize_for_json(value: str) -> str:
    return redact_and_truncate_text(value, MAX_OUTPUT_CHARS)


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
