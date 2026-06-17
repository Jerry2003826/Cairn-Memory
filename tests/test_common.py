from __future__ import annotations

import pytest

from omni._common import (
    TRUNCATION_SUFFIX,
    collapse_whitespace,
    collapse_whitespace_command,
    truncate_with_suffix,
)


def test_truncate_with_suffix_reports_flag_and_uses_shared_suffix() -> None:
    truncated, did_truncate = truncate_with_suffix(
        "abcdefghijklmnopqrstuvwxyz",
        len(TRUNCATION_SUFFIX) + 2,
    )

    assert did_truncate is True
    assert truncated == f"ab{TRUNCATION_SUFFIX}"


def test_truncate_with_suffix_rejects_unusable_limit() -> None:
    with pytest.raises(ValueError, match="truncation suffix"):
        truncate_with_suffix("abcdef", len(TRUNCATION_SUFFIX))


def test_collapse_whitespace_helpers_share_command_behavior() -> None:
    assert collapse_whitespace("  pnpm   run\t test\n") == "pnpm run test"
    assert collapse_whitespace_command("  pnpm   run\t test\n") == "pnpm run test"
