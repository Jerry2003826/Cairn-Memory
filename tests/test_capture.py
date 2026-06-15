"""Tests for capture engine registry and Claude engine constants."""

from __future__ import annotations

import pytest

from omni.capture import CaptureEngine, default, get, register
from omni.capture.claude import EVENT_ROLES, INGEST_EVENTS


def test_default_engine_is_claude() -> None:
    engine = default()
    assert engine.name == "claude"
    assert engine.run_engine == "claude_code"


def test_get_unknown_engine_raises() -> None:
    with pytest.raises(ValueError, match="unknown capture engine"):
        get("nonexistent")


def test_register_rejects_duplicate_engine() -> None:
    duplicate = CaptureEngine(name="claude", ingest_events=frozenset())
    with pytest.raises(ValueError, match="already registered"):
        register(duplicate)


def test_claude_engine_ingest_events_match_legacy_literals() -> None:
    assert INGEST_EVENTS == frozenset({"Stop", "SessionEnd"})
    assert default().ingest_events == INGEST_EVENTS


def test_claude_engine_event_roles_match_legacy_reconcile_order() -> None:
    assert EVENT_ROLES["reconcile_preference"] == (
        "PostToolUse",
        "PostToolUseFailure",
        "PreToolUse",
    )
    assert EVENT_ROLES["pre"] == ("PreToolUse",)
    assert EVENT_ROLES["post"] == ("PostToolUse", "PostToolUseFailure")
    assert default().event_roles == EVENT_ROLES


def test_opencode_engine_is_registered_for_run_metadata() -> None:
    engine = get("opencode")

    assert engine.name == "opencode"
    assert engine.run_engine == "opencode"
    assert engine.ingest_events == frozenset()
    assert engine.install is None
    assert engine.event_roles == {}
