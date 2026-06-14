"""Command normalization, directory-change stripping, and expected-command matching."""

from __future__ import annotations

from pathlib import Path
from typing import Any

PACKAGE_MANAGERS = {"bun", "npm", "pnpm", "yarn"}


def _normalize_command(command: str, *, project_root: Path | None = None) -> str:
    return _strip_leading_directory_changes(
        " ".join(command.strip().split()), project_root=project_root
    )


def _strip_leading_directory_changes(
    command: str, *, project_root: Path | None = None
) -> str:
    current = command
    while "&&" in current:
        head, tail = current.split("&&", 1)
        target = _directory_change_target(head)
        if target is None:
            break
        if project_root is None or not _directory_target_exists(target, project_root):
            break
        current = tail.strip()
    return current


def _directory_change_target(command: str) -> str | None:
    stripped = command.strip()
    if not stripped:
        return None
    parts = stripped.split(maxsplit=1)
    if len(parts) != 2:
        return None
    verb, remainder = parts[0].lower(), parts[1].strip()
    if verb not in {"cd", "chdir", "pushd"}:
        return None
    if verb in {"cd", "chdir"} and remainder.lower().startswith("/d "):
        remainder = remainder[3:].strip()
    if not remainder:
        return None
    if remainder[0] in {"'", '"'}:
        quote = remainder[0]
        end = remainder.find(quote, 1)
        if end == -1:
            return None
        return remainder[1:end]
    return remainder.split(maxsplit=1)[0]


def _directory_target_exists(target: str, project_root: Path) -> bool:
    if not target or any(marker in target for marker in ("$", "%", "`")):
        return False
    try:
        candidate = Path(target)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        return candidate.is_dir()
    except (OSError, ValueError):
        return False


def _has_unresolved_directory_change_prefix(command: str, project_root: Path) -> bool:
    collapsed = " ".join(command.strip().split())
    if "&&" not in collapsed:
        return False
    head, _tail = collapsed.split("&&", 1)
    target = _directory_change_target(head)
    return target is not None and not _directory_target_exists(target, project_root)


def _matches_any_expected_command(observed: str, expected_commands: list[str]) -> bool:
    return any(_matches_expected_command(observed, expected) for expected in expected_commands)


def _matches_expected_command(observed: str, expected: str) -> bool:
    observed_norm = _normalize_command(observed)
    expected_norm = _normalize_command(expected)
    if _matches_command_prefix(observed_norm, expected_norm):
        return True
    observed_canonical = _canonical_pm_run_command(observed_norm)
    expected_canonical = _canonical_pm_run_command(expected_norm)
    return _matches_command_prefix(observed_canonical, expected_canonical)


def _matches_command_prefix(observed: str, expected: str) -> bool:
    return observed == expected or observed.startswith(f"{expected} ")


def _canonical_pm_run_command(command: str) -> str:
    tokens = command.split()
    if len(tokens) < 2 or tokens[0] not in PACKAGE_MANAGERS:
        return command
    if len(tokens) >= 3 and tokens[1] == "run":
        return command
    script = tokens[1]
    rest = " ".join(tokens[2:])
    canonical = f"{tokens[0]} run {script}"
    return f"{canonical} {rest}" if rest else canonical


def _path_in_text(value: str, target: str) -> bool:
    normalized_value = value.replace("\\", "/").lower()
    normalized_target = target.replace("\\", "/").lower()
    return normalized_target in normalized_value


def _contains_path(values: Any, target: str) -> bool:
    return any(_path_in_text(value, target) for value in values)


def _looks_like_path(value: str, target: str) -> bool:
    if "\n" in value or "\r" in value:
        return False
    normalized = value.replace("\\", "/").strip().lower()
    normalized_target = target.replace("\\", "/").lower()
    return normalized == normalized_target or normalized.endswith(f"/{normalized_target}")


def _target_detail(value: str, target: str) -> str:
    if _looks_like_path(value, target):
        return f"path: {_normalize_command(value)}"
    if target == "LS":
        return "directory listing"
    return f"matched: {target}"
