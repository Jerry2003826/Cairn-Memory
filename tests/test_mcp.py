from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from omni import mcp
from omni import db
from omni import task
from omni import verify
from omni._common import TASK_TYPE_VALUES
from tests.leak_helpers import assert_no_metadata_leak


REPO_ROOT = Path(__file__).resolve().parents[1]


def connect(tmp_path: Path) -> sqlite3.Connection:
    (tmp_path / ".omni").mkdir(parents=True, exist_ok=True)
    conn = db.connect(tmp_path / ".omni" / "omni.sqlite3")
    db.migrate(conn)
    return conn


def seed_project_facts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO facts(
          fact_id, scope, subject, predicate, qualifier, object_norm, value_type,
          claim, trust, confidence, sensitivity, origin, pinned, created_seq,
          retired_seq, superseded_by, last_confirmed_at, created_at, evidence
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "fact_test_cmd",
            "project",
            ".",
            "uses_test_command",
            "node",
            "pnpm run test",
            "string",
            "Use pnpm run test for Node tests.",
            2,
            None,
            "low",
            "test",
            0,
            1,
            None,
            None,
            None,
            "2026-06-13T00:00:00Z",
            "{}",
        ),
    )
    conn.commit()


def seed_failure_pattern(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO failure_patterns(
          pattern_id, source_failure_cand_id, scope, command_norm, failure_kind,
          error_signature, error_signature_hash, summary, suggested_action, trust,
          status, evidence, created_seq, retired_seq, superseded_by, created_at,
          updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "failure_pattern_mcp",
            "failure_cand_mcp",
            "project",
            "pnpm run test",
            "command_failed",
            "exit 1",
            "hash_mcp",
            "Tests can fail when setup is incomplete.",
            "Run the project test command after fixing setup.",
            2,
            "active",
            "{}",
            1,
            None,
            None,
            "2026-06-17T00:00:00+00:00",
            "2026-06-17T00:00:00+00:00",
        ),
    )
    conn.commit()


def test_mcp_lists_only_readonly_tools(tmp_path: Path) -> None:
    init_response = mcp.handle_request(
        tmp_path,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        },
    )
    assert init_response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "cairn-memory",
                "title": "Cairn Memory",
                "version": "0.1.0",
            },
            "instructions": "Read-only access to Cairn Memory project context.",
        },
    }

    list_response = mcp.handle_request(
        tmp_path,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    tools = list_response["result"]["tools"]

    assert [tool["name"] for tool in tools] == [
        "memory_read",
        "failure_read",
        "verify_plan",
        "task_read",
    ]
    assert all(tool["inputSchema"]["type"] == "object" for tool in tools)
    json.dumps(list_response)


def test_mcp_verify_plan_task_enum_uses_shared_task_type_values() -> None:
    verify_plan_tool = next(
        tool for tool in mcp.tools() if tool["name"] == "verify_plan"
    )

    task_schema = verify_plan_tool["inputSchema"]["properties"]["task"]

    assert task_schema["enum"] == sorted(TASK_TYPE_VALUES)


def test_mcp_tool_call_returns_structured_content(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    seed_project_facts(conn)
    conn.close()

    response = mcp.handle_request(
        tmp_path,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "memory_read", "arguments": {}},
        },
    )

    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["schema_version"] == 1
    assert result["content"] == [
        {
            "type": "text",
            "text": json.dumps(result["structuredContent"], indent=2, sort_keys=True),
        }
    ]
    assert_no_metadata_leak(result)


def test_mcp_verify_plan_tool_does_not_execute_command(
    tmp_path: Path,
    monkeypatch,
) -> None:
    conn = connect(tmp_path)
    seed_project_facts(conn)
    conn.close()

    def fail_if_spawned(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("verify_plan must not execute verification")

    monkeypatch.setattr(verify, "run_preflight", fail_if_spawned)

    response = mcp.handle_request(
        tmp_path,
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "verify_plan", "arguments": {"profile": "test"}},
        },
    )

    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["candidate_commands"] == [
        {"qualifier": "node", "command": "pnpm run test"}
    ]
    assert_no_metadata_leak(result)


def test_mcp_other_read_tools_return_structured_content(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    conn.close()

    for tool_name in ("failure_read", "task_read"):
        response = mcp.handle_request(
            tmp_path,
            {
                "jsonrpc": "2.0",
                "id": tool_name,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": {}},
            },
        )

        result = response["result"]
        assert result["isError"] is False
        assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
        assert_no_metadata_leak(result)


def test_mcp_serve_stdio_smoke(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    seed_project_facts(conn)
    conn.close()

    requests: list[dict[str, Any]] = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "verify_plan", "arguments": {}},
        },
    ]
    stdin = "".join(json.dumps(request) + "\n" for request in requests)

    result = subprocess.run(
        [sys.executable, "-m", "omni.cli", "mcp", "serve"],
        cwd=tmp_path,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert [response["id"] for response in responses] == [1, 2, 3]
    assert responses[1]["result"]["tools"][0]["name"] == "memory_read"
    assert responses[2]["result"]["structuredContent"]["candidate_commands"] == [
        {"qualifier": "node", "command": "pnpm run test"}
    ]


def test_mcp_client_acceptance_harness_calls_all_read_tools(tmp_path: Path) -> None:
    conn = connect(tmp_path)
    seed_project_facts(conn)
    seed_failure_pattern(conn)
    task.start_task(conn, tmp_path, "acceptance task", task_type="bugfix")
    conn.close()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "mcp_client_acceptance.py"),
            "--root",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["tools"] == [
        "memory_read",
        "failure_read",
        "verify_plan",
        "task_read",
    ]

    calls = payload["calls"]
    assert calls["memory_read"]["structuredContent"]["schema_version"] == 1
    assert calls["failure_read"]["structuredContent"][0]["command_norm"] == "pnpm run test"
    assert calls["verify_plan"]["structuredContent"]["candidate_commands"] == [
        {"qualifier": "node", "command": "pnpm run test"}
    ]
    assert calls["task_read"]["structuredContent"]["tasks"] == [
        {
            "run_count": 0,
            "status": "open",
            "task_type": "bugfix",
            "title": "acceptance task",
        }
    ]
    for name in payload["tools"]:
        assert_no_metadata_leak(calls[name]["structuredContent"])


def test_mcp_tool_errors_are_tool_results(tmp_path: Path) -> None:
    response = mcp.handle_request(
        tmp_path,
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "memory_read", "arguments": {}},
        },
    )

    assert response["result"]["isError"] is True
    assert "database" in response["result"]["structuredContent"]["error"]


def test_mcp_tools_use_readonly_connection_without_migrate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    conn = connect(tmp_path)
    seed_project_facts(conn)
    conn.close()

    def fail_migrate(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("MCP tools must not migrate")

    monkeypatch.setattr(db, "migrate", fail_migrate)

    response = mcp.handle_request(
        tmp_path,
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "verify_plan", "arguments": {}},
        },
    )

    assert response["result"]["isError"] is False
