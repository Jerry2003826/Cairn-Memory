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
    args = _resolve_cairn_args(tokens, index)
    if args is None or len(args) < 2:
        return None
    return SURFACE_COMMANDS.get((args[0], args[1]))


def _resolve_cairn_args(tokens: list[str], start: int) -> list[str] | None:
    if start >= len(tokens):
        return None
    if tokens[start] == "uv" and start + 2 < len(tokens) and tokens[start + 1] == "run":
        return _resolve_cairn_args(tokens, start + 2)

    executable = Path(tokens[start]).name
    if executable.lower().endswith(".exe"):
        executable = executable[:-4]

    if executable in {"python", "python3"}:
        if tokens[start + 1 : start + 3] == ["-m", "omni.cli"]:
            return tokens[start + 3 :]
        return None

    if executable in {"cairn", "omni"}:
        return tokens[start + 1 :]
    return None


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
