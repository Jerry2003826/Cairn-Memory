"""Detect read-only Cairn machine-read surface calls in agent commands."""

from __future__ import annotations

import shlex
from pathlib import Path

SURFACE_COMMANDS = {
    ("memory", "read"): "memory_read",
    ("failure", "read"): "failure_read",
    ("verify", "plan"): "verify_plan",
    ("task", "read"): "task_read",
}


def surface_from_command(command: str) -> str | None:
    tokens = _command_tokens(command)
    if not tokens:
        return None
    index = 0
    if tokens[index] == "env":
        index += 1
    while index < len(tokens) and _looks_like_env_assignment(tokens[index]):
        index += 1
    if index >= len(tokens):
        return None

    executable = Path(tokens[index]).name
    if (
        executable in {"python", "python3"}
        and tokens[index + 1 : index + 3] == ["-m", "omni.cli"]
    ):
        args = tokens[index + 3 :]
    elif executable in {"cairn", "omni"}:
        args = tokens[index + 1 :]
    else:
        return None
    if len(args) < 2:
        return None
    return SURFACE_COMMANDS.get((args[0], args[1]))


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _looks_like_env_assignment(token: str) -> bool:
    if "=" not in token or token.startswith("-"):
        return False
    name, _value = token.split("=", 1)
    return bool(name) and all(ch == "_" or ch.isalnum() for ch in name)
