"""Event metadata decoding and nested input navigation."""

from __future__ import annotations

from typing import Any

from omni._event_meta import decode_meta as _decode_meta
from omni._event_meta import nested_command as _nested_command

INPUT_KEYS = {"args", "input", "parameters", "tool_input"}
INPUT_WRAPPER_KEYS = {"hook"}
INPUT_FIELD_KEYS = {
    "cmd",
    "command",
    "filepath",
    "file_path",
    "path",
    "pattern",
}
INPUT_KEY_LOOKUP = {key.lower() for key in INPUT_KEYS}
INPUT_WRAPPER_KEY_LOOKUP = {key.lower() for key in INPUT_WRAPPER_KEYS}
INPUT_FIELD_KEY_LOOKUP = {key.lower() for key in INPUT_FIELD_KEYS}


def _input_metadata(value: Any) -> Any:
    if not isinstance(value, dict):
        return {}
    collected: list[Any] = []
    _collect_input_metadata(value, collected)
    for key, child in value.items():
        if key.lower() in INPUT_WRAPPER_KEY_LOOKUP:
            _collect_input_metadata(child, collected)
    return collected


def _collect_input_metadata(value: Any, collected: list[Any]) -> None:
    if not isinstance(value, dict):
        return
    for key, child in value.items():
        if not _is_input_container_key(key):
            continue
        fields = _input_container_fields(child)
        if _has_content(fields):
            collected.append(fields)


def _input_container_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return [
            {key: child}
            for key, child in value.items()
            if _is_input_field_key(key)
        ]
    if isinstance(value, list):
        return [
            nested
            for child in value
            if _has_content(nested := _input_container_fields(child))
        ]
    return {}


def _is_input_container_key(key: str) -> bool:
    return key.lower() in INPUT_KEY_LOOKUP


def _is_input_field_key(key: str) -> bool:
    return key.lower() in INPUT_FIELD_KEY_LOOKUP


def _has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list, tuple, set, str, bytes)):
        return bool(value)
    return True


def _nested_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            strings.extend(_nested_strings(child))
    elif isinstance(value, list):
        for child in value:
            strings.extend(_nested_strings(child))
    elif isinstance(value, str):
        strings.append(value)
    return strings
