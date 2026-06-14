"""Event metadata decoding and nested input navigation."""

from __future__ import annotations

import json
from typing import Any

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


def _decode_meta(meta_json: str | None) -> dict[str, Any]:
    if not meta_json:
        return {}
    try:
        decoded = json.loads(meta_json)
    except (TypeError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _nested_command(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("command", "cmd"):
            if key in value:
                return value[key]
        for key in ("input", "tool_input", "parameters", "args"):
            found = _nested_command(value.get(key))
            if found is not None:
                return found
        for child in value.values():
            found = _nested_command(child)
            if found is not None:
                return found
    if isinstance(value, list):
        for child in value:
            found = _nested_command(child)
            if found is not None:
                return found
    return None


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
