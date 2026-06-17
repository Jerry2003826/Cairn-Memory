"""Shared file helpers for static extractors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def evidence(root: Path, paths: list[Path]) -> dict[str, object]:
    return {
        "files": [
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "hash": file_hash(path),
            }
            for path in paths
            if path.exists()
        ]
    }


def file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
