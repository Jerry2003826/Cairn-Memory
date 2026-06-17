#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
default_target="${TMPDIR:-/tmp}/cairn-customer-trial-$(date +%Y%m%d-%H%M%S)"
target="${1:-$default_target}"

if [ -n "${PYTHON_BIN:-}" ]; then
  python_bin="$PYTHON_BIN"
elif command -v python3 >/dev/null 2>&1; then
  python_bin="python3"
elif command -v python >/dev/null 2>&1; then
  python_bin="python"
else
  echo "python3 or python is required" >&2
  exit 127
fi

if [ -e "$target/.omni" ]; then
  echo "target already contains .omni; choose a fresh trial path: $target" >&2
  exit 2
fi

export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"

run_cairn() {
  "$python_bin" -m omni.cli "$@"
}

sandbox="$("$repo_root/scripts/create_sandbox.sh" "$target")"
trial_dir="$sandbox/.customer-trial"
mkdir -p "$trial_dir"
cd "$sandbox"

run_cairn init >"$trial_dir/init.txt"
run_cairn audit secrets >"$trial_dir/audit-initial.json"
run_cairn task start "Customer trial validates governed memory in sandbox" \
  --task-type validation >"$trial_dir/task-start.json"
run_cairn ingest customer_trial_bootstrap >"$trial_dir/ingest-bootstrap.txt"
run_cairn render >"$trial_dir/render.txt"
run_cairn inject claude --mode link >"$trial_dir/inject-claude.txt"
run_cairn inject opencode --mode link >"$trial_dir/inject-opencode.txt"
run_cairn inject qwen --mode link >"$trial_dir/inject-qwen.txt"

"$python_bin" - "$trial_dir" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

trial_dir = Path(sys.argv[1])

cold_rows = [
    {
        "type": "tool_use",
        "timestamp": "2026-06-17T00:00:00Z",
        "id": "customer_trial_cold_read_readme",
        "name": "Read",
        "input": {"file_path": "README.md"},
    },
    {
        "type": "tool_use",
        "timestamp": "2026-06-17T00:00:01Z",
        "id": "customer_trial_cold_read_package",
        "name": "Read",
        "input": {"file_path": "package.json"},
    },
    {
        "type": "tool_use",
        "timestamp": "2026-06-17T00:00:02Z",
        "id": "customer_trial_cold_test",
        "name": "Bash",
        "input": {"command": "pnpm run test"},
        "exit_code": 0,
    },
]

warm_rows = [
    {
        "type": "tool_use",
        "timestamp": "2026-06-17T00:01:00Z",
        "id": "customer_trial_warm_memory",
        "name": "Bash",
        "input": {"command": "python -m omni.cli memory read"},
        "exit_code": 0,
    },
    {
        "type": "tool_use",
        "timestamp": "2026-06-17T00:01:01Z",
        "id": "customer_trial_warm_plan",
        "name": "Bash",
        "input": {"command": "python -m omni.cli verify plan"},
        "exit_code": 0,
    },
    {
        "type": "tool_use",
        "timestamp": "2026-06-17T00:01:02Z",
        "id": "customer_trial_warm_test",
        "name": "Bash",
        "input": {"command": "pnpm run test"},
        "exit_code": 0,
    },
]

for name, rows in {"cold.jsonl": cold_rows, "warm.jsonl": warm_rows}.items():
    (trial_dir / name).write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
PY

run_cairn ingest customer_trial_cold \
  --transcript "$trial_dir/cold.jsonl" >"$trial_dir/ingest-cold.txt"
run_cairn ingest customer_trial_warm \
  --transcript "$trial_dir/warm.jsonl" >"$trial_dir/ingest-warm.txt"
run_cairn eval run customer_trial_warm >"$trial_dir/eval-warm.json"
run_cairn eval dogfood \
  --cold customer_trial_cold \
  --warm customer_trial_warm >"$trial_dir/dogfood.json"
run_cairn memory read >"$trial_dir/memory-read.json"
run_cairn failure read >"$trial_dir/failure-read.json"
run_cairn verify plan >"$trial_dir/verify-plan.json"
run_cairn task read >"$trial_dir/task-read.json"
"$python_bin" "$repo_root/scripts/mcp_client_acceptance.py" \
  --root "$sandbox" >"$trial_dir/mcp-acceptance.json"
run_cairn audit secrets >"$trial_dir/audit-final.json"

"$python_bin" - "$sandbox" "$trial_dir" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

sandbox = Path(sys.argv[1])
trial_dir = Path(sys.argv[2])


def load_json(name: str) -> dict:
    return json.loads((trial_dir / name).read_text(encoding="utf-8"))


dogfood = load_json("dogfood.json")
warm_eval = load_json("eval-warm.json")
mcp = load_json("mcp-acceptance.json")
audit = load_json("audit-final.json")
verify_plan = load_json("verify-plan.json")
task_read = load_json("task-read.json")
candidate_commands = verify_plan.get("candidate_commands") or []
verify_command = verify_plan.get("command")
if verify_command is None and len(candidate_commands) == 1:
    verify_command = candidate_commands[0].get("command")
tasks = task_read.get("tasks") or []
open_task_title = tasks[0].get("title") if tasks else None

report = {
    "ok": bool(
        dogfood.get("improvement")
        and mcp.get("ok")
        and audit.get("ok")
        and verify_command
    ),
    "sandbox": str(sandbox),
    "dogfood_improvement": dogfood.get("improvement"),
    "memory_effect": warm_eval.get("memory_effect"),
    "warm_machine_read_surfaces": dogfood.get("warm_machine_read_surfaces", []),
    "first_expected_command": warm_eval.get("first_expected_command"),
    "verify_command": verify_command,
    "mcp_ok": mcp.get("ok"),
    "mcp_tools": mcp.get("tools", []),
    "audit_ok": audit.get("ok"),
    "open_task": open_task_title,
    "created_files": [
        ".omni/generated/memory.md",
        "CLAUDE.md",
        "opencode.json",
        "QWEN.md",
        ".customer-trial/report.json",
    ],
}

report_path = trial_dir / "report.json"
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2, sort_keys=True))
print(f"customer_trial_report: {report_path}")
print(f"sandbox: {sandbox}")
if not report["ok"]:
    raise SystemExit(1)
PY
