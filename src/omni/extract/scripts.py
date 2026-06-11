"""Deterministic command extractor."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from omni.extract import pm
from omni.gate import FactCandidate

ORIGIN = "script_extractor@1"
NPM_DEFAULT_TEST = 'echo "Error: no test specified" && exit 1'

SCRIPT_MAP = {
    "test": ("uses_test_command", "default"),
    "test:unit": ("uses_test_command", "unit"),
    "test:e2e": ("uses_test_command", "e2e"),
    "test:integration": ("uses_test_command", "integration"),
    "build": ("uses_build_command", "default"),
    "lint": ("uses_lint_command", "default"),
    "typecheck": ("uses_typecheck_command", "default"),
    "check:types": ("uses_typecheck_command", "default"),
}


def detect(root: Path) -> list[FactCandidate]:
    commands: dict[tuple[str, str], FactCandidate] = {}
    node_pm = _node_pm(root)
    python_pm = _python_pm(root)

    if node_pm:
        commands.update(_node_commands(root, node_pm))
    if python_pm:
        commands.update(_python_commands(root, python_pm))

    for key, candidate in _make_commands(root).items():
        commands.setdefault(key, candidate)

    return list(commands.values())


def _node_pm(root: Path) -> str | None:
    candidates = [
        candidate
        for candidate in pm.detect(root)
        if candidate.qualifier == "node" and not candidate.conflict_with
    ]
    return candidates[0].object_norm if len(candidates) == 1 else None


def _python_pm(root: Path) -> str | None:
    candidates = [
        candidate
        for candidate in pm.detect(root)
        if candidate.qualifier == "python" and not candidate.conflict_with
    ]
    return candidates[0].object_norm if len(candidates) == 1 else None


def _node_commands(root: Path, pm_name: str) -> dict[tuple[str, str], FactCandidate]:
    package_json = root / "package.json"
    if not package_json.exists():
        return {}
    package = _read_json(package_json)
    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        return {}

    commands: dict[tuple[str, str], FactCandidate] = {}
    for script_name, mapped in SCRIPT_MAP.items():
        if script_name not in scripts:
            continue
        if script_name == "test" and str(scripts[script_name]).strip() == NPM_DEFAULT_TEST:
            continue
        commands[mapped] = _candidate(
            root,
            predicate=mapped[0],
            qualifier=mapped[1],
            object_norm=f"{pm_name} run {script_name}",
            evidence_paths=[package_json],
        )

    dev_script = "dev" if "dev" in scripts else "start" if "start" in scripts else None
    if dev_script:
        key = ("uses_dev_command", "default")
        commands[key] = _candidate(
            root,
            predicate=key[0],
            qualifier=key[1],
            object_norm=f"{pm_name} run {dev_script}",
            evidence_paths=[package_json],
        )
    return commands


def _python_commands(root: Path, pm_name: str) -> dict[tuple[str, str], FactCandidate]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    parsed = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    if _has_pytest_config(parsed):
        key = ("uses_test_command", "default")
        return {
            key: _candidate(
                root,
                predicate=key[0],
                qualifier=key[1],
                object_norm=f"{pm_name} run pytest",
                evidence_paths=[pyproject],
            )
        }
    return {}


def _make_commands(root: Path) -> dict[tuple[str, str], FactCandidate]:
    makefile = root / "Makefile"
    if not makefile.exists():
        return {}
    targets = _make_targets(makefile)
    commands: dict[tuple[str, str], FactCandidate] = {}
    for target, key in {
        "test": ("uses_test_command", "default"),
        "build": ("uses_build_command", "default"),
    }.items():
        if target in targets:
            commands[key] = _candidate(
                root,
                predicate=key[0],
                qualifier=key[1],
                object_norm=f"make {target}",
                evidence_paths=[makefile],
            )
    return commands


def _candidate(
    root: Path,
    *,
    predicate: str,
    qualifier: str,
    object_norm: str,
    evidence_paths: list[Path],
) -> FactCandidate:
    return FactCandidate(
        scope="project",
        subject=".",
        predicate=predicate,
        qualifier=qualifier,
        object_norm=object_norm,
        value_type="string",
        claim=f"Project {predicate.replace('_', ' ')}: {object_norm}",
        trust=2,
        sensitivity="low",
        origin=ORIGIN,
        evidence=_evidence(root, evidence_paths),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _has_pytest_config(parsed: dict[str, Any]) -> bool:
    tool = parsed.get("tool")
    return isinstance(tool, dict) and isinstance(tool.get("pytest"), dict)


def _make_targets(path: Path) -> set[str]:
    targets: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+):", line)
        if match:
            targets.add(match.group(1))
    return targets


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
