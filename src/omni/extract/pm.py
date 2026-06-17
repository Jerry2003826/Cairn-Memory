"""Deterministic package-manager extractor."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from omni.extract.files import evidence, read_json
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
        selected = package_manager_for(root, qualifier, candidates=candidates)
        if selected is not None:
            return selected
    return None


def package_manager_for(
    root: Path,
    qualifier: str,
    *,
    candidates: list[FactCandidate] | None = None,
) -> str | None:
    available = detect(root) if candidates is None else candidates
    selected = [
        candidate
        for candidate in available
        if candidate.qualifier == qualifier and not candidate.conflict_with
    ]
    return selected[0].object_norm if len(selected) == 1 else None


def _detect_node(root: Path) -> list[FactCandidate]:
    package_json = root / "package.json"
    lock_candidates = [
        _candidate(root, "node", pm_name, [root / lock_name])
        for lock_name, pm_name in NODE_LOCKS.items()
        if (root / lock_name).exists()
    ]

    if package_json.exists():
        package = read_json(package_json)
        package_manager_field = package.get("packageManager")
        if isinstance(package_manager_field, str) and package_manager_field:
            pm_name = package_manager_field.split("@", 1)[0]
            if pm_name in NODE_LOCKS.values():
                return [
                    _candidate(
                        root,
                        "node",
                        pm_name,
                        [package_json, *_matching_lock_paths(root, pm_name)],
                    )
                ]

    if len(lock_candidates) > 1:
        ids = [ensure_candidate_id(candidate).cand_id for candidate in lock_candidates]
        return [
            replace(
                ensure_candidate_id(candidate),
                conflict_with=",".join(sorted(set(ids) - {candidate.cand_id})),
            )
            for candidate in lock_candidates
        ]
    return lock_candidates


def _detect_python(root: Path) -> list[FactCandidate]:
    for lock_name, pm_name in PYTHON_LOCKS.items():
        lock_path = root / lock_name
        if lock_path.exists():
            evidence_paths = [lock_path]
            pyproject = root / "pyproject.toml"
            if pyproject.exists():
                evidence_paths.append(pyproject)
            return [_candidate(root, "python", pm_name, evidence_paths)]
    if (root / "requirements.txt").exists():
        return [_candidate(root, "python", "pip", [root / "requirements.txt"])]
    return []


def _candidate(
    root: Path,
    qualifier: str,
    pm_name: str,
    evidence_paths: list[Path],
) -> FactCandidate:
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
        evidence=evidence(root, evidence_paths),
    )


def _matching_lock_paths(root: Path, pm_name: str) -> list[Path]:
    return [
        root / name
        for name, lock_pm in NODE_LOCKS.items()
        if lock_pm == pm_name and (root / name).exists()
    ]
