"""Spool readers for hook and ingest queue records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HookRecord:
    path: Path
    line_no: int
    record: dict[str, Any]
    payload: dict[str, Any]


def spool_dir(root: Path | str) -> Path:
    return Path(root).resolve() / ".omni" / "spool"


def iter_hook_records(root: Path | str) -> list[HookRecord]:
    records: list[HookRecord] = []
    for path in sorted(spool_dir(root).glob("hook-*.jsonl")):
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            try:
                record = json.loads(line)
                payload = json.loads(record.get("payload", "{}"))
            except Exception:
                continue
            if isinstance(record, dict) and isinstance(payload, dict):
                records.append(
                    HookRecord(path=path, line_no=line_no, record=record, payload=payload)
                )
    return records


def drain_ingest_queue(root: Path | str) -> list[dict[str, Any]]:
    directory = spool_dir(root)
    requests: list[dict[str, Any]] = []
    for path in sorted(directory.glob("ingest-*.json")):
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            requests.append(parsed)
            path.unlink(missing_ok=True)

    legacy_path = directory / "ingest_queue.jsonl"
    if legacy_path.exists():
        for line in legacy_path.read_text(encoding="utf-8").splitlines():
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                requests.append(parsed)
        legacy_path.write_text("", encoding="utf-8")
    return requests
