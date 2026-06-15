"""Claude Code capture engine configuration and hook installation."""

from __future__ import annotations

import difflib
import json
import os
import re
import shutil
from pathlib import Path

from omni.capture import CaptureEngine, InstallResult, register
from omni.redact import redact

AUDIT_PASSED_MARKER = Path(".omni") / "audit" / "secrets.passed"
DEFAULT_HOOK_COMMAND = "omni hook"
HOOK_COMMAND_ENV = "OMNI_HOOK_COMMAND"
CLAUDE_HOOK_SETTINGS_BY_SCOPE = {
    "local": "settings.local.json",
    "project": "settings.json",
}

CLAUDE_HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "PermissionRequest",
    "Notification",
    "PreCompact",
    "SubagentStart",
    "SubagentStop",
    "Stop",
    "SessionEnd",
)

MATCHER_EVENTS = {
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "PermissionRequest",
    "SubagentStart",
    "SubagentStop",
    "SessionStart",
    "SessionEnd",
    "Notification",
    "PreCompact",
}

INGEST_EVENTS = frozenset({"Stop", "SessionEnd"})

EVENT_ROLES = {
    "reconcile_preference": ("PostToolUse", "PostToolUseFailure", "PreToolUse"),
    "pre": ("PreToolUse",),
    "post": ("PostToolUse", "PostToolUseFailure"),
}


def install_claude_hooks(
    root: Path | str | None = None,
    *,
    yes: bool = False,
    scope: str = "local",
) -> InstallResult:
    base = Path(root or Path.cwd()).resolve()
    settings_filename = CLAUDE_HOOK_SETTINGS_BY_SCOPE.get(scope)
    if settings_filename is None:
        return InstallResult(ok=False, message=f"invalid Claude hook scope: {scope}")
    if not yes and not (base / AUDIT_PASSED_MARKER).exists():
        return InstallResult(
            ok=False,
            message=(
                "omni audit secrets has not passed in this checkout; rerun with --yes "
                "to install Claude hooks anyway."
            ),
        )

    claude_dir = base / ".claude"
    settings_path = claude_dir / settings_filename
    settings_label = f".claude/{settings_filename}"
    original = settings_path.read_text(encoding="utf-8-sig") if settings_path.exists() else "{}\n"
    try:
        settings = _parse_settings(original, label=settings_label)
    except ValueError as exc:
        return InstallResult(ok=False, message=str(exc))
    hook_command = _hook_command()
    updated = _settings_with_omni_hooks(settings, command=hook_command)
    rendered = json.dumps(updated, indent=2, sort_keys=True) + "\n"
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=settings_label,
            tofile=f"{settings_label} (omni)",
        )
    )

    claude_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(settings_path, rendered)
    return InstallResult(ok=True, diff=_redacted_text(diff))


def _parse_settings(original: str, *, label: str = ".claude/settings.json") -> dict[str, object]:
    try:
        parsed = json.loads(original) if original.strip() else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label}: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"invalid {label}: root must be a JSON object")
    return parsed


def _settings_with_omni_hooks(settings: dict[str, object], *, command: str) -> dict[str, object]:
    updated = dict(settings)
    hooks = updated.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
    else:
        hooks = dict(hooks)

    for event_name in CLAUDE_HOOK_EVENTS:
        groups = hooks.get(event_name)
        if not isinstance(groups, list):
            groups = []
        groups = list(groups)
        groups, found = _upgrade_omni_hooks(groups, command)
        if not found:
            groups.append(_hook_group(event_name, command))
        hooks[event_name] = groups

    updated["hooks"] = hooks
    return updated


def _hook_command() -> str:
    override = os.environ.get(HOOK_COMMAND_ENV)
    if override:
        return override
    return DEFAULT_HOOK_COMMAND


def _hook_group(event_name: str, command: str) -> dict[str, object]:
    group: dict[str, object] = {
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": 5,
            }
        ]
    }
    if event_name in MATCHER_EVENTS:
        group["matcher"] = "*"
    return group


def _upgrade_omni_hooks(groups: list[object], command: str) -> tuple[list[object], bool]:
    upgraded: list[object] = []
    found = False
    for group in groups:
        if not isinstance(group, dict):
            upgraded.append(group)
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            upgraded.append(group)
            continue

        new_handlers: list[object] = []
        group_has_omni = False
        for handler in handlers:
            if not isinstance(handler, dict):
                new_handlers.append(handler)
                continue
            handler_command = handler.get("command")
            if _is_omni_hook_command(handler_command, command):
                if not found:
                    replacement = dict(handler)
                    replacement["command"] = command
                    new_handlers.append(replacement)
                    found = True
                    group_has_omni = True
                continue
            new_handlers.append(handler)

        new_group = dict(group)
        new_group["hooks"] = new_handlers
        if group_has_omni or new_handlers:
            upgraded.append(new_group)
    return upgraded, found


def _is_omni_hook_command(value: object, command: str) -> bool:
    if not isinstance(value, str):
        return False
    if value in {command, DEFAULT_HOOK_COMMAND}:
        return True
    return re.search(r"(^|\s)-m\s+omni\.cli\s+hook(\s|$)", value) is not None


def _atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    temp_path = path.with_name(f"{path.name}.omni-tmp")
    try:
        temp_path.write_text(content, encoding=encoding)
        if path.exists():
            try:
                shutil.copymode(path, temp_path)
            except OSError:
                pass
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def _redacted_text(value: str) -> str:
    return redact(value.encode("utf-8")).data.decode("utf-8", errors="replace")


register(
    CaptureEngine(
        name="claude",
        ingest_events=INGEST_EVENTS,
        run_engine="claude_code",
        install=install_claude_hooks,
        event_roles=EVENT_ROLES,
    )
)
