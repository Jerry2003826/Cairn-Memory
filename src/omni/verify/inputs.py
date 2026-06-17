"""Shared verification input validation."""

from __future__ import annotations

from omni._common import TASK_TYPE_VALUES, validate_choice

PROFILE_VALUES = frozenset({"default", "release", "test"})


def validate_selection_inputs(
    *,
    task_type: str | None,
    profile: str | None,
) -> None:
    if task_type is not None:
        validate_choice("task_type", task_type, TASK_TYPE_VALUES)
    if profile is not None:
        validate_choice("profile", profile, PROFILE_VALUES)
