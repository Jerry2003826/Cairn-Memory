"""Shared event-metadata helpers.

Consolidates two byte-identical clones that previously lived independently:

- ``decode_meta`` — was duplicated as ``eval.meta._decode_meta`` and
  ``failure.meta._decode_meta``.
- ``nested_command`` — was duplicated as ``eval.meta._nested_command`` and
  ``extract.observed._nested_command``.

Note: ``ingest._nested_command`` (depth-limited, extra ``part``/``state`` keys)
and ``failure.meta._nested_command`` (callback-based, str-only) are intentionally
*not* consolidated here — they have genuinely different behavior despite the
shared name.
"""

from __future__ import annotations

import json
from typing import Any


def decode_meta(meta_json: str | None) -> dict[str, Any]:
    if not meta_json:
        return {}
    try:
        decoded = json.loads(meta_json)
    except (TypeError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def nested_command(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("command", "cmd"):
            if key in value:
                return value[key]
        for key in ("input", "tool_input", "parameters", "args"):
            found = nested_command(value.get(key))
            if found is not None:
                return found
        for child in value.values():
            found = nested_command(child)
            if found is not None:
                return found
    if isinstance(value, list):
        for child in value:
            found = nested_command(child)
            if found is not None:
                return found
    return None
