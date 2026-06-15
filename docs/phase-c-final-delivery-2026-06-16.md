# Cairn Memory Phase C Final Delivery Evidence

Date: 2026-06-16 local, with CLI timestamps recorded in UTC.

Update: after this OpenCode/task closeout, C-4 was approved and landed as
`cairn mcp serve`, a read-only stdio MCP wrapper exposing `memory_read`,
`failure_read`, `verify_plan`, and `task_read`. The historical evidence below
still describes the earlier OpenCode/task delivery state.

Scope: approved Phase C only. This closeout covers the already-approved Cairn
Bridge and Cairn Runtime-lite slices: OpenCode v0 config injection, OpenCode
UTF-8 JSONL transcript ingest, read-only machine surfaces, task lifecycle, and
outcome evidence. It does not approve or implement new Phase C rows.

## Boundary

OpenCode remained the coding agent. Cairn Memory was the governed brain layer.
The OpenCode process was only a read-only consumer of Cairn Memory state through
these surfaces:

```powershell
python -m omni.cli memory read
python -m omni.cli failure read
python -m omni.cli verify plan
python -m omni.cli task read
```

Writes still went through human-gated CLI writer commands:

```powershell
python -m omni.cli task start "<intent>" --task-type validation
python -m omni.cli ingest <run_id> --engine opencode --transcript <utf8-jsonl>
python -m omni.cli task close --success --from-verify
python -m omni.cli task close --success --from-verify --profile release
```

The same boundary also holds for the installed command spelling:

```powershell
cairn memory read
cairn failure read
cairn verify plan
cairn task read
cairn ingest --engine opencode --transcript
```

At the time of this closeout, no MCP server had been added. No external write
path, OpenCode plugin background capture, multi-agent router, permission-tier
system, UI, vector search, or LLM extractor were added.

Safety invariants were unchanged:

- redaction-before-write
- hook never writes DB
- read-only commands never migrate
- human-gated CLI writer for task, ingest, and outcome state

## OpenCode multi-sample dogfood

Environment facts:

- Sandbox: disposable local sandbox created by `scripts/create_sandbox.ps1`.
- OpenCode invocation: `npx -y opencode-ai@latest run --format json`.
- Resolved OpenCode version: `1.17.7`.
- Model/provider: sandbox-local OpenCode config for `apiyi/deepseek-chat`.
- Provider credentials: config referenced `{env:APIYI_API_KEY}`. No key was
  printed, committed, or copied into the repo.
- Config sources checked: OpenCode provider/config docs and APIYI OpenCode docs.

Preflight:

```powershell
python -m omni.cli init
python -m omni.cli audit secrets
python -m omni.cli ingest bootstrap_static
python -m omni.cli render
python -m omni.cli inject opencode --mode link
```

`opencode.json` retained the environment placeholder and added one instruction:

```json
{
  "api_key_placeholder_preserved": true,
  "has_base_url": true,
  "has_instruction": true,
  "instruction_count": 1
}
```

Canonical observed writer path:

```powershell
python -m omni.cli ingest <run_id> --engine opencode --transcript <utf8-jsonl>
python -m omni.cli task close --success --from-verify [--profile release]
```

Read surfaces before OpenCode:

```json
{
  "memory": [
    "Use pnpm run test for Node tests.",
    "Use pnpm run build to build Node.",
    "node package manager: pnpm"
  ],
  "failure_read": [],
  "verify_plan": "pnpm run test",
  "task_read": []
}
```

The fresh sandbox had no active known-failure pattern. That is acceptable for
this closeout because this sample proves the read surface and sequencing, while
the earlier C-2 evidence file records a non-empty failure read sample.

### Sample 1: test validation

Intent: OpenCode should use Cairn Memory read surfaces, accept the test command
from `verify plan`, and run it without rediscovering package scripts first.

Run id: `phasec_opencode_test`.

Transcript ingest:

```powershell
python -m omni.cli ingest phasec_opencode_test --engine opencode --transcript opencode-phasec-test.jsonl
```

Ingest output:

```text
run_ids=phasec_opencode_test events_inserted=5 queue_drained=0
```

`run show` command sequence:

| Seq | Command | Exit |
|---:|---|---:|
| 1 | `python -m omni.cli memory read` | 0 |
| 2 | `python -m omni.cli failure read` | 0 |
| 3 | `python -m omni.cli verify plan` | 0 |
| 4 | `python -m omni.cli task read` | 0 |
| 5 | `pnpm run test` | 0 |

Outcome evidence:

```json
{
  "final_command": "pnpm run test",
  "run_id": "phasec_opencode_test",
  "status": "success",
  "task_type": "validation",
  "tests_status": "passed",
  "verify": {
    "command": "pnpm run test",
    "exit_code": 0,
    "reason_code": "passed",
    "selection_mode": "task"
  }
}
```

### Sample 2: release build validation

Intent: OpenCode should use the same read surfaces, ask Cairn Memory for the
release profile plan, and run the build command selected by Cairn Memory.

Run id: `phasec_opencode_build`.

Local pre-check:

```powershell
python -m omni.cli verify plan --profile release
```

Plan output selected:

```json
{
  "predicate": "uses_build_command",
  "profile": "release",
  "selection_mode": "profile",
  "candidate_commands": [
    {
      "command": "pnpm run build",
      "qualifier": "node"
    }
  ]
}
```

Transcript ingest:

```powershell
python -m omni.cli ingest phasec_opencode_build --engine opencode --transcript opencode-phasec-build.jsonl
```

Ingest output:

```text
run_ids=phasec_opencode_build events_inserted=5 queue_drained=0
```

`run show` command sequence:

| Seq | Command | Exit |
|---:|---|---:|
| 1 | `python -m omni.cli memory read` | 0 |
| 2 | `python -m omni.cli failure read` | 0 |
| 3 | `python -m omni.cli verify plan --profile release` | 0 |
| 4 | `python -m omni.cli task read` | 0 |
| 5 | `pnpm run build` | 0 |

Outcome evidence:

```json
{
  "final_command": "pnpm run build",
  "run_id": "phasec_opencode_build",
  "status": "success",
  "task_type": "validation",
  "tests_status": "passed",
  "verify": {
    "command": "pnpm run build",
    "exit_code": 0,
    "profile": "release",
    "reason_code": "passed",
    "selection_mode": "profile"
  }
}
```

Both fresh samples stored `runs.engine = "opencode"` and attached their ingested
runs to the open task that existed when the transcript was ingested.

### Non-counted invocation failures

Three setup attempts were abandoned before any transcript was ingested. They are
not counted as dogfood samples:

- one custom provider run failed before transcript creation
- one official APIYI model run failed before transcript creation
- one Windows `Start-Process` invocation passed malformed arguments before
  transcript creation

Each was closed with `task abandon`; none was marked as successful evidence.

## Verification Evidence

Sandbox audit after each successful OpenCode ingest and task close:

```json
{
  "fixtures_missing": false,
  "negative_failures": [],
  "ok": true,
  "omni_leaks": [],
  "positive_failures": []
}
```

Repository-level gates for this delivery use:

| Gate | Result |
|---|---|
| `npx -y opencode-ai@latest --version` | 1.17.7 |
| `python -m pytest tests/test_docs.py -q` | 14 passed |
| `python -m pytest tests/test_cli_smoke.py tests/test_db.py tests/test_task.py -q` | 131 passed, 3 skipped |
| `pytest -q` | 622 passed, 3 skipped |
| `git diff --check` | pass |
| `python -m omni.cli audit secrets` | ok=true |

Machine-readable gate anchors:

- `npx -y opencode-ai@latest --version`: 1.17.7
- `python -m pytest tests/test_docs.py -q`: 14 passed
- `python -m pytest tests/test_cli_smoke.py tests/test_db.py tests/test_task.py -q`: 131 passed, 3 skipped
- `pytest -q`: 622 passed, 3 skipped
- `git diff --check`: pass
- `python -m omni.cli audit secrets`: ok=true

## Implemented and verified

- C-1/C-3 Cairn Bridge foundation: capture/inject seams and stable read-only
  machine surfaces.
- C-2 OpenCode v0: project-local `opencode.json` instruction injection and
  UTF-8 `opencode run --format json` transcript ingest through
  `cairn ingest --engine opencode --transcript`.
- C-5 Runtime-lite task lifecycle: one open operational task, task read view,
  task close with verify/outcome evidence.
- OpenCode multi-sample dogfood: two fresh samples in one disposable sandbox,
  both reading Cairn Memory state before command execution.
- Safety gates: sandbox `python -m omni.cli audit secrets` passed after the
  OpenCode ingest and close steps.

This evidence is stronger than the original single C-2 sample because it covers
two fresh OpenCode runs and two verification profiles: test and release build.
It still does not prove broad behavioral improvement across many cold/warm
OpenCode task families.

## Implemented but needs more dogfood samples

- OpenCode v0 is implemented and proved for bounded validation/build tasks, but
  it needs more dogfood samples across bugfix, refactor, and failure-recovery
  prompts before claiming broad behavior improvement.
- Failure read is implemented and previously proved with a non-empty pattern,
  but this fresh sandbox had no active known-failure pattern.
- The task lifecycle is implemented for a single open task; multi-agent handoff
  remains outside this approved slice.

## Explicitly not implemented at this closeout

- No MCP server at this closeout. C-4 later landed as a read-only stdio wrapper.
- No external write path for OpenCode, Codex, QwenCode, Cursor, or any other
  agent.
- No OpenCode background plugin or automatic capture loop.
- No multi-engine router or replacement coding agent.
- No permission-tier product surface.
- No UI, dashboard, TUI, or team account system.
- No vector or embedding search.
- No LLM extractor or automatic memory evolution.

## Next smallest high-value tasks

1. Run three more OpenCode dogfood samples: one bugfix, one refactor, and one
   known-failure recovery prompt.
2. Add one fresh non-empty `failure read` OpenCode sample in a sandbox where the
   known-failure pattern is created through the existing extract and approve
   writers.
3. If the charter approves C-4, build only a read-only MCP wrapper over the
   existing read surfaces, with no DB write capability.
4. Keep the next adapter work at the same boundary: read governed Cairn Memory
   state, capture only redacted transcripts, and write only through human-gated
   Cairn CLI commands.
