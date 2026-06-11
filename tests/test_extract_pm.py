from __future__ import annotations

import sqlite3
from pathlib import Path

from omni import db
from omni import gate
from omni.extract import scripts


REPOS = Path(__file__).parent / "fixtures" / "repos"


def process_repo(tmp_path: Path, name: str) -> sqlite3.Connection:
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")
    db.migrate(conn)
    gate.extract_static_facts(REPOS / name, conn)
    return conn


def facts(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT scope, subject, predicate, qualifier, object_norm, trust, origin
        FROM facts
        WHERE retired_seq IS NULL
        ORDER BY predicate, qualifier, object_norm
        """
    ).fetchall()
    return [dict(row) for row in rows]


def pending_pm_candidates(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT cand_id, subject, predicate, qualifier, object_norm, conflict_with, state
        FROM fact_candidates
        WHERE predicate = 'uses_package_manager'
        ORDER BY object_norm
        """
    ).fetchall()
    return [dict(row) for row in rows]


def test_a1_node_pnpm_package_manager_auto_commits(tmp_path: Path) -> None:
    conn = process_repo(tmp_path, "node-pnpm")

    assert {
        "scope": "project",
        "subject": ".",
        "predicate": "uses_package_manager",
        "qualifier": "node",
        "object_norm": "pnpm",
        "trust": 2,
        "origin": "pm_detector@1",
    } in facts(conn)


def test_a4_node_npm_lockfile_auto_commits(tmp_path: Path) -> None:
    conn = process_repo(tmp_path, "node-npm")

    assert {
        "scope": "project",
        "subject": ".",
        "predicate": "uses_package_manager",
        "qualifier": "node",
        "object_norm": "npm",
        "trust": 2,
        "origin": "pm_detector@1",
    } in facts(conn)


def test_a6_node_multilock_conflicts_stay_pending(tmp_path: Path) -> None:
    conn = process_repo(tmp_path, "node-multilock")

    candidates = pending_pm_candidates(conn)
    assert [candidate["object_norm"] for candidate in candidates] == ["npm", "pnpm"]
    assert all(candidate["state"] == "pending" for candidate in candidates)
    assert all(candidate["conflict_with"] for candidate in candidates)
    assert not facts(conn)


def test_a7_python_uv_detects_pm_with_python_qualifier(tmp_path: Path) -> None:
    conn = process_repo(tmp_path, "python-uv")

    assert {
        "scope": "project",
        "subject": ".",
        "predicate": "uses_package_manager",
        "qualifier": "python",
        "object_norm": "uv",
        "trust": 2,
        "origin": "pm_detector@1",
    } in facts(conn)


def test_a12_monorepo_root_pnpm_detected_and_path_subjects_deferred(tmp_path: Path) -> None:
    conn = process_repo(tmp_path, "monorepo-pnpm")

    root_facts = [
        fact
        for fact in facts(conn)
        if fact["predicate"] == "uses_package_manager" and fact["qualifier"] == "node"
    ]
    assert root_facts == [
        {
            "scope": "project",
            "subject": ".",
            "predicate": "uses_package_manager",
            "qualifier": "node",
            "object_norm": "pnpm",
            "trust": 2,
            "origin": "pm_detector@1",
        }
    ]
    assert (REPOS / "monorepo-pnpm" / "A12_DEFERRED.md").read_text(encoding="utf-8")


def test_python_pip_repo_with_pytest_hint_uses_plain_pytest_command(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project.optional-dependencies]\ndev = ['pytest']\n",
        encoding="utf-8",
    )

    candidates = scripts.detect(tmp_path)
    commands = {
        (candidate.predicate, candidate.qualifier): candidate.object_norm
        for candidate in candidates
    }

    assert commands[("uses_test_command", "python")] == "pytest"
    assert "pip run pytest" not in commands.values()
