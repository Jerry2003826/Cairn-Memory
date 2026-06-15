from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from omni import db
from omni.dbaccess import connect_project_readonly
from omni.ids import project_id_for_path


def connect(tmp_path: Path) -> sqlite3.Connection:
    (tmp_path / ".omni").mkdir(parents=True, exist_ok=True)
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")
    db.migrate(conn)
    return conn


def test_migration_008_creates_tasks_and_sets_schema_version(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    assert db.schema_version(conn) == "8"
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert "tasks" in tables
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(runs)").fetchall()
    }
    assert "task_id" in columns
    conn.close()


def test_migration_007_to_008_preserves_existing_runs(tmp_path: Path) -> None:
    (tmp_path / ".omni").mkdir()
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")
    for version, filename in db.MIGRATIONS:
        if int(version) > 7:
            break
        conn.executescript(f"BEGIN;\n{db.migration_sql(filename)}\nCOMMIT;")
    conn.commit()
    conn.execute(
        """
        INSERT INTO runs(run_id, project_id, snapshot_seq, status)
        VALUES('run_legacy', ?, 0, 'closed')
        """,
        (project_id_for_path(tmp_path),),
    )
    conn.commit()
    assert db.schema_version(conn) == "7"
    conn.close()

    conn = connect(tmp_path)
    row = conn.execute(
        "SELECT run_id, task_id FROM runs WHERE run_id = 'run_legacy'"
    ).fetchone()
    assert row is not None
    assert row["task_id"] is None
    assert db.schema_version(conn) == "8"
    conn.close()


def test_readonly_rejects_schema_version_7(tmp_path: Path) -> None:
    (tmp_path / ".omni").mkdir()
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")
    for version, filename in db.MIGRATIONS:
        if int(version) > 7:
            break
        conn.executescript(f"BEGIN;\n{db.migration_sql(filename)}\nCOMMIT;")
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="found 7, need 8"):
        connect_project_readonly(tmp_path)
