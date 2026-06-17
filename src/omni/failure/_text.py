"""Shared text normalization helpers for failure extraction."""

from __future__ import annotations

from omni._common import collapse_whitespace, truncate_with_suffix
from omni.jsonio import redact_text

MAX_ERROR_CHARS = 300
MAX_EXCERPT_CHARS = 300
MAX_COMMAND_CHARS = 200
MAX_REVIEW_TEXT_CHARS = 800


def _required_redacted_text(name: str, value: str | None) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{name} is required")
    return truncate_text(redact_text(value.strip()), MAX_REVIEW_TEXT_CHARS)


def truncate_text(value: str | None, max_chars: int) -> str:
    if value is None:
        return ""
    return truncate_with_suffix(collapse_whitespace(value), max_chars)[0]
