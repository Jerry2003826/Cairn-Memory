from __future__ import annotations

import sqlite3
from pathlib import Path

from omni import db
from omni import gate
from omni.extract import scripts
from omni.qualifiers import is_root_scoped_qualifier, scoped_qualifier


REPOS = Path(__file__).parent / "fixtures" / "repos"


def process_repo(tmp_path: Path, name: str) -> sqlite3.Connection:
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")
    db.migrate(conn)
    gate.extract_static_facts(REPOS / name, conn)
    return conn


def command_facts(conn: sqlite3.Connection) -> dict[tuple[str, str], str]:
    rows = conn.execute(
        """
        SELECT predicate, qualifier, object_norm
        FROM facts
        WHERE predicate LIKE 'uses_%_command' AND retired_seq IS NULL
        """
    ).fetchall()
    return {(row["predicate"], row["qualifier"]): row["object_norm"] for row in rows}


def command_fact_rows(conn: sqlite3.Connection) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT subject, predicate, qualifier, object_norm
        FROM facts
        WHERE predicate LIKE 'uses_%_command' AND retired_seq IS NULL
        ORDER BY subject, predicate, qualifier, object_norm
        """
    ).fetchall()
    return [dict(row) for row in rows]


def test_a2_a3_node_pnpm_test_and_build_commands(tmp_path: Path) -> None:
    commands = command_facts(process_repo(tmp_path, "node-pnpm"))

    assert commands[("uses_test_command", "node")] == "pnpm run test"
    assert commands[("uses_build_command", "node")] == "pnpm run build"


def test_a5_node_npm_default_placeholder_test_is_ignored(tmp_path: Path) -> None:
    commands = command_facts(process_repo(tmp_path, "node-npm"))

    assert ("uses_test_command", "node") not in commands


def test_a8_python_uv_test_command(tmp_path: Path) -> None:
    commands = command_facts(process_repo(tmp_path, "python-uv"))

    assert commands[("uses_test_command", "python")] == "uv run pytest"


def test_a9_python_poetry_test_command(tmp_path: Path) -> None:
    commands = command_facts(process_repo(tmp_path, "python-poetry"))

    assert commands[("uses_test_command", "python")] == "poetry run pytest"


def test_python_optional_dev_dependency_detects_pytest(tmp_path: Path) -> None:
    commands = command_facts(process_repo(tmp_path, "python-optional-pytest"))

    assert commands[("uses_test_command", "python")] == "uv run pytest"


def test_mixed_node_python_repo_preserves_both_test_commands(tmp_path: Path) -> None:
    commands = command_facts(process_repo(tmp_path, "mixed-node-python"))

    assert commands[("uses_test_command", "node")] == "pnpm run test"
    assert commands[("uses_test_command", "python")] == "uv run pytest"


def test_a10_a11_make_only_commands(tmp_path: Path) -> None:
    commands = command_facts(process_repo(tmp_path, "make-only"))

    assert commands[("uses_test_command", "default")] == "make test"
    assert commands[("uses_build_command", "default")] == "make build"


def test_monorepo_workspace_package_test_command_uses_package_subject(
    tmp_path: Path,
) -> None:
    rows = command_fact_rows(process_repo(tmp_path, "monorepo-pnpm"))

    assert {
        "subject": "packages/app",
        "predicate": "uses_test_command",
        "qualifier": "node:app",
        "object_norm": "pnpm --dir packages/app run test",
    } in rows


def test_qualifier_helpers_document_root_scope_boundary() -> None:
    assert scoped_qualifier("node", None) == "node"
    assert scoped_qualifier("node", "app") == "node:app"
    assert is_root_scoped_qualifier("node") is True
    assert is_root_scoped_qualifier("node:unit") is False
    assert is_root_scoped_qualifier("node:@scope/pkg") is False


def test_node_workspace_run_command_templates(tmp_path: Path) -> None:
    root = tmp_path
    package_dir = root / "packages" / "app"
    package_dir.mkdir(parents=True)
    package = {"name": "@scope/app"}

    cases = {
        "npm": "npm run test --workspace=@scope/app",
        "pnpm": "pnpm --dir packages/app run test",
        "yarn": "yarn workspace @scope/app test",
        "bun": "bun --cwd packages/app run test",
    }

    for pm_name, expected in cases.items():
        assert (
            scripts._node_run_command(
                pm_name,
                "test",
                package_dir=package_dir,
                package=package,
                root=root,
            )
            == expected
        )
