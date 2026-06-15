from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from omni import db
from omni import ingest
from omni import task
from omni.dbaccess import connect_project_readonly
from omni.ids import project_id_for_path


def connect(tmp_path: Path) -> sqlite3.Connection:
    (tmp_path / ".omni").mkdir(parents=True, exist_ok=True)
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")
    db.migrate(conn)
    return conn


def seed_run(conn: sqlite3.Connection, tmp_path: Path, run_id: str = "run_task_test") -> None:
    conn.execute(
        """
        INSERT INTO runs(run_id, project_id, snapshot_seq, status, started_at)
        VALUES(?,?,?,?,?)
        """,
        (run_id, project_id_for_path(tmp_path), 0, "closed", "2026-06-15T00:00:00Z"),
    )
    conn.commit()


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


def test_task_start_and_status(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    started = task.start_task(conn, tmp_path, "fix the flaky test", task_type="bugfix")
    assert started["status"] == "open"
    assert started["title"] == "fix the flaky test"
    status = task.task_status(conn, tmp_path)
    assert status["open"]["task_id"] == started["task_id"]
    assert status["attached_run_count"] == 0
    conn.close()


def test_double_start_is_refused(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    task.start_task(conn, tmp_path, "first intent")
    with pytest.raises(ValueError, match="open task already exists"):
        task.start_task(conn, tmp_path, "second intent")
    conn.close()


def test_ingest_attaches_run_to_open_task(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    started = task.start_task(conn, tmp_path, "attach run")
    ingest._ensure_run(conn, tmp_path, "run_attached", None)
    conn.commit()
    row = conn.execute(
        "SELECT task_id FROM runs WHERE run_id = 'run_attached'"
    ).fetchone()
    assert row["task_id"] == started["task_id"]
    conn.close()


def test_ingest_without_task_leaves_task_id_null(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    ingest._ensure_run(conn, tmp_path, "run_unattached", None)
    conn.commit()
    row = conn.execute(
        "SELECT task_id FROM runs WHERE run_id = 'run_unattached'"
    ).fetchone()
    assert row["task_id"] is None
    conn.close()


def test_close_task_records_outcome_on_representative_run(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    started = task.start_task(conn, tmp_path, "close me", task_type="validation")
    seed_run(conn, tmp_path, "run_close")
    conn.execute(
        "UPDATE runs SET task_id = ? WHERE run_id = 'run_close'",
        (started["task_id"],),
    )
    conn.commit()
    closed = task.close_task(conn, tmp_path, status="success")
    assert closed["status"] == "closed"
    assert closed["outcome_status"] == "success"
    outcome = conn.execute(
        "SELECT status FROM outcomes WHERE run_id = 'run_close'"
    ).fetchone()
    assert outcome["status"] == "success"
    assert task.current_task_id_for_ingest(conn) is None
    conn.close()


def test_close_without_runs_sets_not_run_tests_status(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    task.start_task(conn, tmp_path, "close empty")
    closed = task.close_task(conn, tmp_path, status="unknown")
    assert closed["tests_status"] == "not_run"
    assert closed["outcome_status"] == "unknown"
    conn.close()


def test_abandon_clears_current_task_pointer(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    task.start_task(conn, tmp_path, "give up")
    abandoned = task.abandon_task(conn, tmp_path, reason="blocked")
    assert abandoned["status"] == "abandoned"
    assert task.current_task_id_for_ingest(conn) is None
    conn.close()


def test_transition_to_closed_is_idempotent(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    started = task.start_task(conn, tmp_path, "once")
    now = "2026-06-15T00:00:00Z"
    task._transition_task(conn, started["task_id"], target="closed", now=now)
    task._transition_task(conn, started["task_id"], target="closed", now=now)
    conn.close()
