"""Deterministic package-manager extractor."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from omni.gate import FactCandidate, ensure_candidate_id

ORIGIN = "pm_detector@1"

NODE_LOCKS = {
    "pnpm-lock.yaml": "pnpm",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "bun.lock": "bun",
    "bun.lockb": "bun",
}

PYTHON_LOCKS = {
    "uv.lock": "uv",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
}


def detect(root: Path) -> list[FactCandidate]:
    return [*_detect_node(root), *_detect_python(root)]


def package_manager(root: Path) -> str | None:
    candidates = detect(root)
    for qualifier in ("node", "python"):
        selected = [candidate for candidate in candidates if candidate.qualifier == qualifier]
        if len(selected) == 1 and not selected[0].conflict_with:
            return selected[0].object_norm
    return None


def _detect_node(root: Path) -> list[FactCandidate]:
    package_json = root / "package.json"
    lock_candidates = [
        _candidate(root, "node", pm_name, [root / lock_name])
        for lock_name, pm_name in NODE_LOCKS.items()
        if (root / lock_name).exists()
    ]

    if package_json.exists():
        package = _read_json(package_json)
        package_manager_field = package.get("packageManager")
        if isinstance(package_manager_field, str) and package_manager_field:
            pm_name = package_manager_field.split("@", 1)[0]
            return [_candidate(root, "node", pm_name, [package_json, *_matching_lock_paths(root, pm_name)])]

    if len(lock_candidates) > 1:
        ids = [ensure_candidate_id(candidate).cand_id for candidate in lock_candidates]
        return [
            replace(ensure_candidate_id(candidate), conflict_with=",".join(sorted(set(ids) - {candidate.cand_id})))
            for candidate in lock_candidates
        ]
    return lock_candidates


def _detect_python(root: Path) -> list[FactCandidate]:
    for lock_name, pm_name in PYTHON_LOCKS.items():
        lock_path = root / lock_name
        if lock_path.exists():
            evidence = [lock_path]
            pyproject = root / "pyproject.toml"
            if pyproject.exists():
                evidence.append(pyproject)
            return [_candidate(root, "python", pm_name, evidence)]
    if (root / "requirements.txt").exists():
        return [_candidate(root, "python", "pip", [root / "requirements.txt"])]
    return []


def _candidate(root: Path, qualifier: str, pm_name: str, evidence_paths: list[Path]) -> FactCandidate:
    return FactCandidate(
        scope="project",
        subject=".",
        predicate="uses_package_manager",
        qualifier=qualifier,
        object_norm=pm_name,
        value_type="string",
        claim=f"Project uses {pm_name} package manager",
        trust=2,
        sensitivity="low",
        origin=ORIGIN,
        evidence=_evidence(root, evidence_paths),
    )


def _matching_lock_paths(root: Path, pm_name: str) -> list[Path]:
    return [root / name for name, lock_pm in NODE_LOCKS.items() if lock_pm == pm_name and (root / name).exists()]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _evidence(root: Path, paths: list[Path]) -> dict[str, object]:
    return {
        "files": [
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "hash": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in paths
            if path.exists()
        ]
    }
