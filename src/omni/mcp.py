"""Read-only MCP stdio wrapper for Cairn Memory machine views."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from omni import __version__
from omni._common import TASK_TYPE_VALUES

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "cairn-memory"
SERVER_TITLE = "Cairn Memory"

JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603


def handle_request(root: Path | str, request: dict[str, Any]) -> dict[str, Any] | None:
    if request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
        return _error(request.get("id"), JSONRPC_INVALID_REQUEST, "Invalid JSON-RPC request")
    request_id = request.get("id")
    method = request.get("method")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _response(request_id, _initialize_result())
    if method == "tools/list":
        return _response(request_id, {"tools": tools()})
    if method == "tools/call":
        return _response(request_id, _call_tool(root, request.get("params")))
    if method == "ping":
        return _response(request_id, {})
    return _error(request_id, JSONRPC_METHOD_NOT_FOUND, f"Unknown method: {method}")


def serve_stdio(
    root: Path | str,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    for line in input_stream:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, JSONRPC_PARSE_ERROR, "Parse error")
        else:
            if not isinstance(request, dict):
                response = _error(None, JSONRPC_INVALID_REQUEST, "Invalid JSON-RPC request")
            else:
                try:
                    response = handle_request(root, request)
                except Exception as exc:
                    print(f"cairn mcp internal error: {exc}", file=sys.stderr)
                    response = _error(
                        request.get("id"),
                        JSONRPC_INTERNAL_ERROR,
                        "Internal error",
                    )
        if response is None:
            continue
        output_stream.write(json.dumps(response, sort_keys=True, separators=(",", ":")) + "\n")
        output_stream.flush()
    return 0


def tools() -> list[dict[str, Any]]:
    empty_input = {"type": "object", "properties": {}, "additionalProperties": False}
    verify_plan_input = {
        "type": "object",
        "properties": {
            "qualifier": {"type": "string"},
            "task": {
                "type": "string",
                "enum": sorted(TASK_TYPE_VALUES),
            },
            "profile": {"type": "string", "enum": ["default", "release", "test"]},
        },
        "additionalProperties": False,
    }
    return [
        {
            "name": "memory_read",
            "title": "Read Project Memory",
            "description": "Read rendered Cairn Memory project context as structured JSON.",
            "inputSchema": empty_input,
        },
        {
            "name": "failure_read",
            "title": "Read Known Failures",
            "description": "Read active known-failure patterns as structured JSON.",
            "inputSchema": empty_input,
        },
        {
            "name": "verify_plan",
            "title": "Plan Verification",
            "description": "Return the selected verification command without executing it.",
            "inputSchema": verify_plan_input,
        },
        {
            "name": "task_read",
            "title": "Read Open Task",
            "description": "Read the current project's open task context as structured JSON.",
            "inputSchema": empty_input,
        },
    ]


def _initialize_result() -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {
            "name": SERVER_NAME,
            "title": SERVER_TITLE,
            "version": __version__,
        },
        "instructions": "Read-only access to Cairn Memory project context.",
    }


def _call_tool(root: Path | str, params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        return _tool_error("tools/call params must be an object")
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if not isinstance(name, str) or not name:
        return _tool_error("tool name is required")
    if not isinstance(arguments, dict):
        return _tool_error("tool arguments must be an object")

    try:
        payload = _tool_payload(Path(root), name, arguments)
    except (FileNotFoundError, ValueError) as exc:
        return _tool_error(str(exc))

    return _tool_result(payload)


def _tool_payload(root: Path, name: str, arguments: dict[str, Any]) -> Any:
    from omni import render
    from omni import task
    from omni import verify
    from omni.dbaccess import connect_project_readonly
    from omni.failure.repo import read_view as failure_read_view

    conn = connect_project_readonly(root)
    try:
        if name == "memory_read":
            return render.read_view(conn)
        if name == "failure_read":
            return failure_read_view(conn)
        if name == "verify_plan":
            return verify.plan_view(
                conn,
                qualifier=arguments.get("qualifier"),
                task_type=arguments.get("task"),
                profile=arguments.get("profile"),
            )
        if name == "task_read":
            return task.read_view(conn)
    finally:
        conn.close()
    raise ValueError(f"Unknown tool: {name}")


def _tool_result(payload: Any) -> dict[str, Any]:
    text = _tool_text(payload)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": False,
    }


def _tool_error(message: str) -> dict[str, Any]:
    payload = {"error": message}
    return {
        "content": [{"type": "text", "text": _tool_text(payload)}],
        "structuredContent": payload,
        "isError": True,
    }


def _tool_text(payload: Any) -> str:
    from omni.redact import redact

    encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    return redact(encoded).data.decode("utf-8", errors="replace")


def _response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }
