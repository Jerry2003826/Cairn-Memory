"""Deterministic project memory renderer."""

from __future__ import annotations

import difflib
import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from omni import db

RENDER_VER = 1
BLOCK_ID = "project_memory"
GENERATED_PATH = Path(".omni") / "generated" / "memory.md"
HEADER_RE = re.compile(
    r"^<!-- omni:generated render_ver=1 sha256=([0-9a-f]{64}) DO NOT EDIT -->\r?\n"
)
MAX_BODY_CHARS = 6000


@dataclass(frozen=True)
class RenderResult:
    path: Path
    body: str
    diff: str
    wrote: bool
    dirty: bool


class ManualEditError(RuntimeError):
    def __init__(self, diff: str) -> None:
        super().__init__("generated memory was manually edited; rerun with --force to overwrite")
        self.diff = diff


def connect_project(root: Path | str | None = None) -> sqlite3.Connection:
    base = Path(root or Path.cwd()).resolve()
    conn = db.connect(base / ".omni" / "omni.sqlite3")
    db.migrate(conn)
    return conn


def render_project(
    conn: sqlite3.Connection,
    root: Path | str,
    *,
    diff: bool = False,
    force: bool = False,
) -> RenderResult:
    base = Path(root).resolve()
    path = base / GENERATED_PATH
    facts = _active_facts(conn)
    body, line_hashes = _render_body(facts)
    text = _with_header(body)
    rendered_diff = _diff(path, text)

    if diff:
        return RenderResult(path=path, body=text, diff=rendered_diff, wrote=False, dirty=False)

    if path.exists() and not force and _manual_edit_detected(path):
        raise ManualEditError(rendered_diff)

    dirty = _update_block_state(conn, body, line_hashes)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    conn.commit()
    return RenderResult(path=path, body=text, diff=rendered_diff, wrote=True, dirty=dirty)


def _active_facts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT fact_id, scope, subject, predicate, qualifier, object_norm
        FROM facts
        WHERE retired_seq IS NULL
        ORDER BY predicate, qualifier, subject, object_norm
        """
    ).fetchall()


def _render_body(facts: list[sqlite3.Row]) -> tuple[str, dict[str, str]]:
    sections: dict[str, list[tuple[str, str]]] = {
        "Commands": [],
        "Boundaries": [],
        "Project": [],
    }

    for fact in facts:
        rendered = _render_fact_line(fact)
        if rendered is None:
            continue
        section, line = rendered
        sections[section].append((fact["fact_id"], line))

    line_hashes: dict[str, str] = {}
    lines = ["# Project memory", ""]
    for section in ("Commands", "Boundaries", "Project"):
        lines.append(f"## {section}")
        for fact_id, line in sections[section]:
            if _body_length(lines) + len(line) + 1 > MAX_BODY_CHARS:
                break
            lines.append(line)
            line_hashes[fact_id] = _sha256(line)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n", line_hashes


def _render_fact_line(fact: sqlite3.Row) -> tuple[str, str] | None:
    predicate = fact["predicate"]
    qualifier = fact["qualifier"]
    object_norm = fact["object_norm"]

    if predicate.startswith("uses_") and predicate.endswith("_command"):
        command_kind = predicate.removeprefix("uses_").removesuffix("_command").replace("_", " ")
        return ("Commands", f"- {qualifier} {command_kind} command: {object_norm}")

    if predicate == "uses_package_manager":
        return ("Project", f"- {qualifier} package manager: {object_norm}")

    if predicate.startswith(("boundary_", "prefers_", "avoids_")):
        label = predicate.replace("_", " ")
        return ("Boundaries", f"- {label}: {object_norm}")

    label = predicate.replace("_", " ")
    return ("Project", f"- {qualifier} {label}: {object_norm}")


def _with_header(body: str) -> str:
    return f"<!-- omni:generated render_ver={RENDER_VER} sha256={_sha256(body)} DO NOT EDIT -->\n{body}"


def _manual_edit_detected(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    match = HEADER_RE.match(text)
    if not match:
        return True
    body = text[match.end() :]
    return _sha256(body) != match.group(1)


def _update_block_state(
    conn: sqlite3.Connection,
    body: str,
    line_hashes: dict[str, str],
) -> bool:
    previous = {
        row["dep_id"]: row["dep_line_hash"]
        for row in conn.execute(
            "SELECT dep_id, dep_line_hash FROM block_deps WHERE block_id = ? AND dep_kind = 'fact'",
            (BLOCK_ID,),
        )
    }
    block_exists = conn.execute("SELECT 1 FROM blocks WHERE block_id = ?", (BLOCK_ID,)).fetchone()
    dirty = block_exists is None or previous != line_hashes
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO blocks(block_id, scope, render_ver, content_hash, body, dirty, updated_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(block_id) DO UPDATE SET
          scope = excluded.scope,
          render_ver = excluded.render_ver,
          content_hash = excluded.content_hash,
          body = excluded.body,
          dirty = excluded.dirty,
          updated_at = excluded.updated_at
        """,
        (BLOCK_ID, "project", RENDER_VER, _sha256(body), body, 1 if dirty else 0, now),
    )
    conn.execute("DELETE FROM block_deps WHERE block_id = ?", (BLOCK_ID,))
    conn.executemany(
        """
        INSERT INTO block_deps(block_id, dep_kind, dep_id, dep_line_hash)
        VALUES(?,?,?,?)
        """,
        [(BLOCK_ID, "fact", fact_id, line_hash) for fact_id, line_hash in line_hashes.items()],
    )
    return dirty


def _diff(path: Path, rendered: str) -> str:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=str(GENERATED_PATH),
            tofile=f"{GENERATED_PATH} (omni)",
        )
    )


def _body_length(lines: list[str]) -> int:
    return sum(len(line) + 1 for line in lines)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
