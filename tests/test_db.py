from __future__ import annotations

import sqlite3
from pathlib import Path

from omni import db


EXPECTED_TABLES = {
    "artifacts",
    "block_deps",
    "blocks",
    "events",
    "fact_candidates",
    "facts",
    "meta",
    "runs",
    "suppressions",
}


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def test_connect_sets_required_pragmas(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")

    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_migration_creates_schema_and_seed_meta(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")

    db.migrate(conn)

    assert table_names(conn) == EXPECTED_TABLES
    assert dict(conn.execute("SELECT key, value FROM meta")) == {
        "schema_version": "1",
        "commit_seq": "0",
        "redaction_ver": "1",
    }
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migration_is_idempotent(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")

    db.migrate(conn)
    db.migrate(conn)

    assert table_names(conn) == EXPECTED_TABLES
    assert conn.execute("SELECT COUNT(*) FROM meta").fetchone()[0] == 3


def test_migration_sql_does_not_set_pragmas() -> None:
    sql = db.migration_sql("001_init.sql")
    executable_sql = "\n".join(
        line for line in sql.splitlines() if not line.strip().startswith("--")
    )

    assert "PRAGMA journal_mode=WAL;" not in executable_sql
    assert "PRAGMA busy_timeout=5000;" not in executable_sql
    assert "PRAGMA foreign_keys=ON;" not in executable_sql
