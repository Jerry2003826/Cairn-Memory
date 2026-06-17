"""Observed command extractor from ingested tool events."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from omni._common import collapse_whitespace_command
from omni._event_meta import nested_command as _nested_command
from omni.gate import FactCandidate

ORIGIN = "observed_command@1"
COMMAND_TOOLS = {"Bash", "PowerShell", "bash", "run_shell_command"}


def detect(conn: sqlite3.Connection) -> list[FactCandidate]:
    rows = conn.execute(
        """
        SELECT run_id, seq, tool, meta
        FROM events
        WHERE tool IN ('Bash', 'PowerShell', 'bash', 'run_shell_command')
        ORDER BY run_id, seq
        """
    ).fetchall()
    candidates: dict[tuple[str, str, str], FactCandidate] = {}
    for row in rows:
        command = _command_from_meta(row["meta"])
        if command is None:
            continue
        command = collapse_whitespace_command(command)
        mapped = _classify(command)
        if mapped is None:
            continue
        predicate, qualifier = mapped
        key = (predicate, qualifier, command)
        candidates.setdefault(
            key,
            FactCandidate(
                scope="project",
                subject=".",
                predicate=predicate,
                qualifier=qualifier,
                object_norm=command,
                value_type="string",
                claim=f"Observed project {predicate.replace('_', ' ')}: {command}",
                trust=1,
                sensitivity="low",
                origin=ORIGIN,
                run_id=row["run_id"],
                evidence={
                    "events": [
                        {
                            "run_id": row["run_id"],
                            "seq": row["seq"],
                            "tool": row["tool"],
                        }
                    ]
                },
            ),
        )
    return list(candidates.values())


def _command_from_meta(meta_json: str | None) -> str | None:
    if not meta_json:
        return None
    try:
        meta = json.loads(meta_json)
    except json.JSONDecodeError:
        return None
    command = _nested_command(meta)
    if command is None:
        return None
    return str(command)


def _classify(command: str) -> tuple[str, str] | None:
    lowered = command.lower()
    if lowered in {
        "pnpm test",
        "pnpm run test",
        "npm test",
        "npm run test",
        "yarn test",
        "yarn run test",
        "bun test",
        "bun run test",
        "pytest",
        "uv run pytest",
        "poetry run pytest",
        "make test",
    }:
        return ("uses_test_command", "default")
    return None
