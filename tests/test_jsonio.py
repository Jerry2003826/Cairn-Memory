"""Tests for omni.jsonio helpers."""

from __future__ import annotations

import json

from omni import jsonio


def test_redact_text_returns_none_for_none_input() -> None:
    assert jsonio.redact_text(None) is None


def test_redact_text_passes_through_clean_strings() -> None:
    assert jsonio.redact_text("hello world") == "hello world"


def test_redact_mapping_str_redacts_secret_values() -> None:
    secret = "sk-" + "jsoniomappingsecretvalue1234567890"
    encoded = jsonio.redact_mapping_str({"token": secret})

    assert secret not in encoded
    assert "REDACTED:" in encoded


def test_decode_json_dict_returns_default_on_invalid_json() -> None:
    assert jsonio.decode_json_dict(None, default={"fallback": True}) == {"fallback": True}
    assert jsonio.decode_json_dict("not-json", default={"fallback": True}) == {"fallback": True}
    assert jsonio.decode_json_dict('["list"]', default={"fallback": True}) == {"fallback": True}


def test_decode_json_dict_parses_valid_object() -> None:
    assert jsonio.decode_json_dict('{"ok": true}') == {"ok": True}


def test_is_redaction_wrapper_detects_stub_payloads() -> None:
    assert jsonio.is_redaction_wrapper('{"error":"redaction_failed"}') is True
    assert jsonio.is_redaction_wrapper('{"error":"payload_truncated"}') is True
    assert jsonio.is_redaction_wrapper('{"ok": true}') is False


def test_as_json_redacts_and_formats_output() -> None:
    secret = "ghp_" + "abcdefghijklmnopqrstuvwxyz1234567890"
    rendered = jsonio.as_json({"message": secret})

    assert secret not in rendered
    assert rendered.endswith("\n")
    parsed = json.loads(rendered)
    assert "REDACTED:" in parsed["message"]
