"""Acceptance client for the read-only Cairn Memory MCP stdio server."""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

EXPECTED_TOOLS = ["memory_read", "failure_read", "verify_plan", "task_read"]


class StdioMcpClient:
    def __init__(self, *, root: Path, timeout_seconds: float, env: dict[str, str]) -> None:
        self.root = root
        self.timeout_seconds = timeout_seconds
        self._next_id = 1
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._process = subprocess.Popen(
            [sys.executable, "-m", "omni.cli", "mcp", "serve"],
            cwd=root,
            env=env,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert self._process.stdout is not None
        self._reader = threading.Thread(
            target=self._read_stdout,
            args=(self._process.stdout,),
            daemon=True,
        )
        self._reader.start()

    def _read_stdout(self, stream: Any) -> None:
        try:
            for line in stream:
                self._lines.put(line)
        finally:
            self._lines.put(None)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._write(payload)
        response = self._read_response()
        if response.get("id") != request_id:
            raise RuntimeError(f"unexpected response id: {response!r}")
        if "error" in response:
            raise RuntimeError(f"MCP request failed: {response['error']}")
        return response["result"]

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._write(payload)

    def close(self) -> None:
        if self._process.stdin is not None and not self._process.stdin.closed:
            self._process.stdin.close()
        try:
            self._process.wait(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            self._process.wait(timeout=self.timeout_seconds)
        if self._process.returncode != 0:
            stderr = self._process.stderr.read() if self._process.stderr else ""
            raise RuntimeError(f"MCP server exited {self._process.returncode}: {stderr}")

    def _write(self, payload: dict[str, Any]) -> None:
        if self._process.stdin is None:
            raise RuntimeError("MCP server stdin is unavailable")
        self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

    def _read_response(self) -> dict[str, Any]:
        try:
            line = self._lines.get(timeout=self.timeout_seconds)
        except queue.Empty as exc:
            raise TimeoutError("timed out waiting for MCP response") from exc
        if line is None:
            stderr = self._process.stderr.read() if self._process.stderr else ""
            raise RuntimeError(f"MCP server closed stdout before response: {stderr}")
        response = json.loads(line)
        if not isinstance(response, dict):
            raise RuntimeError(f"invalid MCP response: {response!r}")
        return response


def run_acceptance(root: Path, *, timeout_seconds: float) -> dict[str, Any]:
    env = os.environ.copy()
    client = StdioMcpClient(root=root, timeout_seconds=timeout_seconds, env=env)
    try:
        init = client.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "cairn-mcp-acceptance", "version": "1.0.0"},
            },
        )
        client.notify("notifications/initialized")
        listed = client.request("tools/list")
        tool_names = [tool["name"] for tool in listed["tools"]]
        if tool_names != EXPECTED_TOOLS:
            raise RuntimeError(f"unexpected tools: {tool_names!r}")

        calls: dict[str, Any] = {}
        for name in EXPECTED_TOOLS:
            result = client.request(
                "tools/call",
                {"name": name, "arguments": {}},
            )
            if result.get("isError") is not False:
                raise RuntimeError(f"{name} returned an error result: {result!r}")
            if "structuredContent" not in result:
                raise RuntimeError(f"{name} did not return structuredContent")
            calls[name] = {
                "content_types": [item.get("type") for item in result.get("content", [])],
                "structured_type": type(result["structuredContent"]).__name__,
                "structuredContent": result["structuredContent"],
            }
        return {
            "ok": True,
            "server": init["serverInfo"],
            "tools": tool_names,
            "calls": calls,
        }
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Call Cairn Memory read-only MCP tools through a real stdio client.",
    )
    parser.add_argument("--root", default=".", help="Project root to run cairn mcp serve in")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    args = parser.parse_args(argv)

    try:
        result = run_acceptance(Path(args.root).resolve(), timeout_seconds=args.timeout_seconds)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
