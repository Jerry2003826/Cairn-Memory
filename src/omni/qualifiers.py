"""Shared qualifier helpers for command facts and verification selection."""

from __future__ import annotations

QUALIFIER_SCOPE_SEPARATOR = ":"


def scoped_qualifier(base: str, suffix: str | None) -> str:
    return base if suffix is None else f"{base}{QUALIFIER_SCOPE_SEPARATOR}{suffix}"


def is_root_scoped_qualifier(qualifier: str) -> bool:
    return QUALIFIER_SCOPE_SEPARATOR not in qualifier.strip()
