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
from omni.qualifiers import scoped_qualifier

ORIGIN = "script_extractor@1"
NPM_DEFAULT_TEST = 'echo "Error: no test specified" && exit 1'
PYTHON_TEST_COMMANDS = {
    "pip": "pytest",
    "uv": "uv run pytest",
    "poetry": "poetry run pytest",
    "pipenv": "pipenv run pytest",
}

SCRIPT_MAP = {
    "test": ("uses_test_command", "node"),
    "test:unit": ("uses_test_command", "node:unit"),
    "test:e2e": ("uses_test_command", "node:e2e"),
    "test:integration": ("uses_test_command", "node:integration"),
    "build": ("uses_build_command", "node"),
    "lint": ("uses_lint_command", "node"),
    "typecheck": ("uses_typecheck_command", "node"),
    "check:types": ("uses_typecheck_command", "node"),
}


def detect(root: Path) -> list[FactCandidate]:
    commands: dict[tuple[str, str, str], FactCandidate] = {}
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


def _node_commands(root: Path, pm_name: str) -> dict[tuple[str, str, str], FactCandidate]:
    package_json = root / "package.json"
    if not package_json.exists():
        return {}
    package = _read_json(package_json)
    commands = _node_commands_for_package(
        root,
        package_json=package_json,
        package=package,
        package_dir=root,
        pm_name=pm_name,
        subject=".",
        qualifier_suffix=None,
    )
    commands.update(_workspace_node_commands(root, package, pm_name))
    return commands


def _node_commands_for_package(
    root: Path,
    *,
    package_json: Path,
    package: dict[str, Any],
    package_dir: Path,
    pm_name: str,
    subject: str,
    qualifier_suffix: str | None,
) -> dict[tuple[str, str, str], FactCandidate]:
    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    commands: dict[tuple[str, str, str], FactCandidate] = {}
    for script_name, mapped in SCRIPT_MAP.items():
        if script_name not in scripts:
            continue
        if script_name == "test" and str(scripts[script_name]).strip() == NPM_DEFAULT_TEST:
            continue
        qualifier = scoped_qualifier(mapped[1], qualifier_suffix)
        key = (mapped[0], qualifier, subject)
        commands[key] = _candidate(
            root,
            predicate=mapped[0],
            qualifier=qualifier,
            object_norm=_node_run_command(
                pm_name,
                script_name,
                package_dir=package_dir,
                package=package,
                root=root,
            ),
            subject=subject,
            evidence_paths=[package_json],
        )

    dev_script = "dev" if "dev" in scripts else "start" if "start" in scripts else None
    if dev_script:
        qualifier = scoped_qualifier("node", qualifier_suffix)
        key = ("uses_dev_command", qualifier, subject)
        commands[key] = _candidate(
            root,
            predicate="uses_dev_command",
            qualifier=qualifier,
            object_norm=_node_run_command(
                pm_name,
                dev_script,
                package_dir=package_dir,
                package=package,
                root=root,
            ),
            subject=subject,
            evidence_paths=[package_json],
        )
    return commands


def _workspace_node_commands(
    root: Path, root_package: dict[str, Any], pm_name: str
) -> dict[tuple[str, str, str], FactCandidate]:
    commands: dict[tuple[str, str, str], FactCandidate] = {}
    for package_dir in _workspace_package_dirs(root, root_package):
        package_json = package_dir / "package.json"
        package = _read_json(package_json)
        if not package:
            continue
        subject = str(package_dir.relative_to(root)).replace("\\", "/")
        suffix = _workspace_qualifier_suffix(package, subject)
        commands.update(
            _node_commands_for_package(
                root,
                package_json=package_json,
                package=package,
                package_dir=package_dir,
                pm_name=pm_name,
                subject=subject,
                qualifier_suffix=suffix,
            )
        )
    return commands


def _workspace_package_dirs(root: Path, package: dict[str, Any]) -> list[Path]:
    patterns = _workspace_patterns(package.get("workspaces"))
    dirs: list[Path] = []
    for pattern in patterns:
        if pattern.startswith("/") or ".." in Path(pattern).parts or "**" in pattern:
            continue
        for candidate in sorted(root.glob(pattern)):
            if (
                candidate.is_dir()
                and not candidate.is_symlink()
                and (candidate / "package.json").is_file()
            ):
                dirs.append(candidate)
    seen: set[Path] = set()
    unique: list[Path] = []
    for directory in dirs:
        resolved = directory.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(directory)
    return unique


def _workspace_patterns(workspaces: Any) -> list[str]:
    if isinstance(workspaces, list):
        return [item for item in workspaces if isinstance(item, str)]
    if isinstance(workspaces, dict):
        packages = workspaces.get("packages")
        if isinstance(packages, list):
            return [item for item in packages if isinstance(item, str)]
    return []


def _workspace_qualifier_suffix(package: dict[str, Any], subject: str) -> str:
    name = package.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return subject


def _node_run_command(
    pm_name: str,
    script_name: str,
    *,
    package_dir: Path,
    package: dict[str, Any],
    root: Path,
) -> str:
    if package_dir == root:
        return f"{pm_name} run {script_name}"
    subject = str(package_dir.relative_to(root)).replace("\\", "/")
    name = package.get("name")
    workspace = name.strip() if isinstance(name, str) and name.strip() else subject
    if pm_name == "npm":
        return f"npm run {script_name} --workspace={workspace}"
    if pm_name == "pnpm":
        return f"pnpm --dir {subject} run {script_name}"
    if pm_name == "yarn":
        return f"yarn workspace {workspace} {script_name}"
    if pm_name == "bun":
        return f"bun --cwd {subject} run {script_name}"
    return f"{pm_name} run {script_name}"


def _python_commands(root: Path, pm_name: str) -> dict[tuple[str, str, str], FactCandidate]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    try:
        parsed = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}
    if _has_pytest_hint(parsed):
        command = PYTHON_TEST_COMMANDS.get(pm_name)
        if command is None:
            return {}
        key = ("uses_test_command", "python")
        return {
            (*key, "."): _candidate(
                root,
                predicate=key[0],
                qualifier=key[1],
                object_norm=command,
                evidence_paths=[pyproject],
            )
        }
    return {}


def _make_commands(root: Path) -> dict[tuple[str, str, str], FactCandidate]:
    makefile = root / "Makefile"
    if not makefile.exists():
        return {}
    targets = _make_targets(makefile)
    commands: dict[tuple[str, str, str], FactCandidate] = {}
    for target, key in {
        "test": ("uses_test_command", "default"),
        "build": ("uses_build_command", "default"),
    }.items():
        if target in targets:
            commands[(*key, ".")] = _candidate(
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
    subject: str = ".",
) -> FactCandidate:
    return FactCandidate(
        scope="project",
        subject=subject,
        predicate=predicate,
        qualifier=qualifier,
        object_norm=object_norm,
        value_type="string",
        claim=f"Project {predicate.replace('_', ' ')} for {subject}: {object_norm}",
        trust=2,
        sensitivity="low",
        origin=ORIGIN,
        evidence=_evidence(root, evidence_paths),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _has_pytest_hint(parsed: dict[str, Any]) -> bool:
    return (
        _has_pytest_config(parsed)
        or _project_optional_dependencies_include_pytest(parsed)
        or _dependency_groups_include_pytest(parsed)
        or _poetry_dependencies_include_pytest(parsed)
    )


def _has_pytest_config(parsed: dict[str, Any]) -> bool:
    tool = parsed.get("tool")
    return isinstance(tool, dict) and isinstance(tool.get("pytest"), dict)


def _project_optional_dependencies_include_pytest(parsed: dict[str, Any]) -> bool:
    project = parsed.get("project")
    if not isinstance(project, dict):
        return False
    optional = project.get("optional-dependencies")
    if not isinstance(optional, dict):
        return False
    return any(_dependency_list_includes_pytest(group) for group in optional.values())


def _dependency_groups_include_pytest(parsed: dict[str, Any]) -> bool:
    groups = parsed.get("dependency-groups")
    if not isinstance(groups, dict):
        return False
    return any(_dependency_list_includes_pytest(group) for group in groups.values())


def _poetry_dependencies_include_pytest(parsed: dict[str, Any]) -> bool:
    tool = parsed.get("tool")
    if not isinstance(tool, dict):
        return False
    poetry = tool.get("poetry")
    if not isinstance(poetry, dict):
        return False

    dev_dependencies = poetry.get("dev-dependencies")
    if isinstance(dev_dependencies, dict) and _dependency_dict_includes_pytest(dev_dependencies):
        return True

    groups = poetry.get("group")
    if not isinstance(groups, dict):
        return False
    for group in groups.values():
        if isinstance(group, dict):
            dependencies = group.get("dependencies")
            if isinstance(dependencies, dict) and _dependency_dict_includes_pytest(dependencies):
                return True
    return False


def _dependency_list_includes_pytest(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return any(_dependency_name(item) == "pytest" for item in value)


def _dependency_dict_includes_pytest(value: dict[str, Any]) -> bool:
    return any(name.lower() == "pytest" for name in value)


def _dependency_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)", value)
    return match.group(1).lower() if match else None


def _make_targets(path: Path) -> set[str]:
    targets: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return targets
    for line in lines:
        match = re.match(r"^([A-Za-z0-9_.-]+):", line)
        if match:
            targets.add(match.group(1))
    return targets


def _evidence(root: Path, paths: list[Path]) -> dict[str, object]:
    return {
        "files": [
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "hash": _file_hash(path),
            }
            for path in paths
            if path.exists()
        ]
    }


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
