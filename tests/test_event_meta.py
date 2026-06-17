"""Tests for the shared omni._event_meta module.

These cover the two byte-identical clones that were consolidated:
- decode_meta (was eval.meta._decode_meta == failure.meta._decode_meta)
- nested_command (was eval.meta._nested_command == extract.observed._nested_command)
"""

from __future__ import annotations

import json

from omni import _event_meta


# --- decode_meta -----------------------------------------------------------

def test_decode_meta_none_returns_empty() -> None:
    assert _event_meta.decode_meta(None) == {}


def test_decode_meta_empty_string_returns_empty() -> None:
    assert _event_meta.decode_meta("") == {}


def test_decode_meta_valid_dict() -> None:
    payload = json.dumps({"command": "pytest", "n": 1})
    assert _event_meta.decode_meta(payload) == {"command": "pytest", "n": 1}


def test_decode_meta_invalid_json_returns_empty() -> None:
    assert _event_meta.decode_meta("{not json") == {}


def test_decode_meta_non_dict_json_returns_empty() -> None:
    assert _event_meta.decode_meta(json.dumps([1, 2, 3])) == {}


# --- nested_command --------------------------------------------------------

def test_nested_command_direct_command_key() -> None:
    assert _event_meta.nested_command({"command": "ls -la"}) == "ls -la"


def test_nested_command_cmd_key() -> None:
    assert _event_meta.nested_command({"cmd": "make build"}) == "make build"


def test_nested_command_through_input_wrappers() -> None:
    value = {"tool_input": {"args": {"command": "pnpm test"}}}
    assert _event_meta.nested_command(value) == "pnpm test"


def test_nested_command_fallback_scans_all_values() -> None:
    # eval/observed behavior: also scans arbitrary child values, not just
    # the known input wrapper keys.
    value = {"unexpected": {"deep": {"command": "deep-cmd"}}}
    assert _event_meta.nested_command(value) == "deep-cmd"


def test_nested_command_in_list() -> None:
    value = [{"noise": 1}, {"command": "found"}]
    assert _event_meta.nested_command(value) == "found"


def test_nested_command_missing_returns_none() -> None:
    assert _event_meta.nested_command({"foo": "bar"}) is None


# --- the consolidated modules re-export identical behavior -----------------

def test_eval_meta_reexports_shared_functions() -> None:
    from omni.eval import meta as eval_meta

    assert eval_meta._decode_meta is _event_meta.decode_meta
    assert eval_meta._nested_command is _event_meta.nested_command


def test_failure_meta_reexports_decode_meta() -> None:
    from omni.failure import meta as failure_meta

    assert failure_meta._decode_meta is _event_meta.decode_meta


def test_observed_reexports_nested_command() -> None:
    from omni.extract import observed

    assert observed._nested_command is _event_meta.nested_command
