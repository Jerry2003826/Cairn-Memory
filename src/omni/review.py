"""Non-interactive review operations for fact candidates."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from omni import db
from omni import gate


@dataclass(frozen=True)
class ReviewResult:
    cand_id: str
    state: str

    def as_json(self) -> str:
        return json.dumps({"cand_id": self.cand_id, "state": self.state}, sort_keys=True) + "\n"


def connect_project(root: Path | str | None = None) -> sqlite3.Connection:
    base = Path(root or Path.cwd()).resolve()
    conn = db.connect(base / ".omni" / "omni.sqlite3")
    db.migrate(conn)
    return conn


def approve(conn: sqlite3.Connection, cand_id: str) -> ReviewResult:
    candidate = _load_candidate(conn, cand_id)
    gate.insert_fact(conn, candidate)
    conn.execute(
        "UPDATE fact_candidates SET state = ?, reviewed_at = ? WHERE cand_id = ?",
        ("approved", _now(), cand_id),
    )
    conn.commit()
    return ReviewResult(cand_id=cand_id, state="approved")


def reject(conn: sqlite3.Connection, cand_id: str) -> ReviewResult:
    candidate = _load_candidate(conn, cand_id)
    conn.execute(
        """
        INSERT OR IGNORE INTO suppressions(scope, subject, predicate, qualifier, object_norm, created_at)
        VALUES(?,?,?,?,?,?)
        """,
        (
            candidate.scope,
            candidate.subject,
            candidate.predicate,
            candidate.qualifier,
            candidate.object_norm,
            _now(),
        ),
    )
    conn.execute(
        "UPDATE fact_candidates SET state = ?, reviewed_at = ? WHERE cand_id = ?",
        ("rejected", _now(), cand_id),
    )
    conn.commit()
    return ReviewResult(cand_id=cand_id, state="rejected")


def _load_candidate(conn: sqlite3.Connection, cand_id: str) -> gate.FactCandidate:
    row = conn.execute("SELECT * FROM fact_candidates WHERE cand_id = ?", (cand_id,)).fetchone()
    if row is None:
        raise KeyError(cand_id)
    return gate.FactCandidate(
        cand_id=row["cand_id"],
        run_id=row["run_id"],
        scope=row["scope"],
        subject=row["subject"],
        predicate=row["predicate"],
        qualifier=row["qualifier"],
        object_norm=row["object_norm"],
        value_type=row["value_type"],
        claim=row["claim"],
        trust=row["trust"],
        sensitivity="low",
        origin=row["extractor_version"],
        evidence=json.loads(row["evidence"]),
        conflict_with=row["conflict_with"],
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
