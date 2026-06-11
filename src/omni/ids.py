"""Identifier helpers for OmniMemory records."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path


def new_id(prefix: str) -> str:
    safe_prefix = prefix.strip().replace("-", "_")
    if not safe_prefix or not safe_prefix.replace("_", "").isalnum():
        raise ValueError("prefix must contain only letters, digits, hyphen, or underscore")
    return f"{safe_prefix}_{uuid.uuid4().hex}"


def project_id_for_path(path: Path | str) -> str:
    normalized = str(Path(path).resolve()).replace("\\", "/").lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"proj_{digest[:16]}"
