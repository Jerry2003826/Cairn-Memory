"""Tests for omni.jsonio helpers."""

from __future__ import annotations

import json
from unittest import mock

from omni import jsonio
from omni.redact import RedactionResult


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


def test_dump_json_fails_closed_when_blob_redaction_withheld() -> None:
    """I-01: when the whole-blob redact() returns a failure wrapper, dump_json
    must NOT fall back to the original (unredacted) content."""
    secret = "sk-failclosed-supersecret-0987654321"
    wrapper = b'{"byte_len":99,"error":"redaction_failed","payload_sha256":"deadbeef"}'

    with mock.patch(
        "omni.jsonio.redact",
        return_value=RedactionResult(
            data=wrapper, status="withheld", detectors=("withheld",)
        ),
    ):
        # No string_sanitizer -> encoded holds the raw secret; the buggy
        # fallback would leak it.
        rendered = jsonio.dump_json({"token": secret})

    assert secret not in rendered
    assert "redaction_failed" in rendered


def test_is_redaction_wrapper_returns_false_for_invalid_json() -> None:
    """I-01 supporting fix: invalid JSON is not a redaction wrapper."""
    assert jsonio.is_redaction_wrapper("not json at all") is False
    assert jsonio.is_redaction_wrapper("") is False
