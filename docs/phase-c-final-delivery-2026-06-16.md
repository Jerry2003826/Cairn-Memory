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

The initial validation/build sandbox had no active known-failure pattern. That
is acceptable for that sample because it proves the read surface and sequencing;
the follow-up section below records a fresh non-empty failure-read recovery run.

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

## OpenCode follow-up dogfood: bugfix, refactor, and known-failure recovery

Update: the next requested OpenCode dogfood set was run on 2026-06-16 in a
disposable macOS sandbox. This extends the earlier validation/build evidence
with three additional task families: bugfix, refactor, and known-failure
recovery.

The sandbox-local `opencode.json` was copied from the local QwenCode provider
shape into OpenCode's provider schema. No credential was written to the repo or
sandbox config; the config kept environment placeholders only:

```json
{
  "apiyi_api_key_placeholder": true,
  "deepseek_api_key_placeholder": true,
  "instructions": [
    ".omni/generated/memory.md"
  ],
  "model": "qwen-apiyi/glm-5.1",
  "providers": [
    "qwen-apiyi",
    "qwen-deepseek"
  ]
}
```

OpenCode was launched headlessly with:

```powershell
opencode run --format json --model qwen-apiyi/glm-5.1 --agent build --dangerously-skip-permissions
```

Because the macOS sandbox had `python3` but not `python`, OpenCode's first
literal `python -m omni.cli memory read` attempt exited `127` in each follow-up
sample. The agent recovered by using `python3 -m omni.cli ...`; the successful
read-surface calls and verification commands below are the counted evidence.

### Follow-up setup: non-empty known failure

Before the recovery sample, a known-failure pattern was created through the
approved writer path:

```powershell
python3 -m omni.cli ingest opencode_known_failure_seed --engine opencode --transcript opencode-known-failure-seed.jsonl
python3 -m omni.cli failure extract opencode_known_failure_seed
python3 -m omni.cli failure approve failure_cand_aa0596e1256c434c835509be96249c12 --summary "Build can fail when dependency resolution fails while reading the lockfile." --suggested-action "Inspect pnpm-lock.yaml first; preserve pnpm and repair the lockfile before retrying pnpm run build."
python3 -m omni.cli render
```

The resulting `failure read` surface was non-empty:

```json
[
  {
    "command_norm": "pnpm run build",
    "suggested_action": "Inspect pnpm-lock.yaml first; preserve pnpm and repair the lockfile before retrying pnpm run build.",
    "summary": "Build can fail when dependency resolution fails while reading the lockfile."
  }
]
```

### Follow-up sample 3: bugfix

Intent: OpenCode should read Cairn surfaces, use the bugfix task-aware verify
plan, observe the failing unit test, repair the smallest code bug, and rerun the
same selected command.

Run id: `opencode_dogfood_bugfix`.

Transcript ingest:

```text
run_ids=opencode_dogfood_bugfix events_inserted=21 queue_drained=0
```

Key `run show` command sequence:

| Seq | Command | Exit |
|---:|---|---:|
| 3 | `python3 -m omni.cli memory read` | 0 |
| 5 | `python3 -m omni.cli failure read` | 0 |
| 7 | `python3 -m omni.cli verify plan --task bugfix` | 0 |
| 9 | `python3 -m omni.cli task read` | 0 |
| 11 | `pnpm run test:unit` | 1 |
| 16 | edit `math.js` |  |
| 18 | write corrected `math.js` |  |
| 20 | `pnpm run test:unit` | 0 |

Outcome evidence:

```json
{
  "final_command": "pnpm run test:unit",
  "run_id": "opencode_dogfood_bugfix",
  "status": "success",
  "task_type": "bugfix",
  "tests_status": "passed"
}
```

### Follow-up sample 4: refactor

Intent: OpenCode should read Cairn surfaces, use the refactor verify plan,
remove duplicate formatting logic without changing exports, and run the selected
verification command.

Run id: `opencode_dogfood_refactor`.

Transcript ingest:

```text
run_ids=opencode_dogfood_refactor events_inserted=14 queue_drained=0
```

Key `run show` command sequence:

| Seq | Command | Exit |
|---:|---|---:|
| 3 | `python3 -m omni.cli memory read` | 0 |
| 4 | `python3 -m omni.cli failure read` | 0 |
| 5 | `python3 -m omni.cli verify plan --task refactor` | 0 |
| 6 | `python3 -m omni.cli task read` | 0 |
| 11 | edit `format.js` |  |
| 13 | `pnpm run test` | 0 |

Outcome evidence:

```json
{
  "final_command": "pnpm run test",
  "run_id": "opencode_dogfood_refactor",
  "status": "success",
  "task_type": "refactor",
  "tests_status": "passed"
}
```

### Follow-up sample 5: known-failure recovery

Intent: OpenCode should read a non-empty `failure read`, run the release build,
hit the known lockfile failure, inspect `pnpm-lock.yaml`, preserve pnpm, repair
the lockfile, and rerun the release build successfully.

Run id: `opencode_dogfood_known_failure_recovery`.

Transcript ingest:

```text
run_ids=opencode_dogfood_known_failure_recovery events_inserted=17 queue_drained=0
```

Key `run show` command sequence:

| Seq | Command | Exit |
|---:|---|---:|
| 3 | `python3 -m omni.cli memory read` | 0 |
| 5 | `python3 -m omni.cli failure read` | 0 |
| 7 | `python3 -m omni.cli verify plan --profile release` | 0 |
| 8 | `python3 -m omni.cli task read` | 0 |
| 10 | `pnpm run build` | 1 |
| 12 | read `pnpm-lock.yaml` |  |
| 14 | edit `pnpm-lock.yaml` |  |
| 16 | `pnpm run build` | 0 |

Outcome evidence:

```json
{
  "final_command": "pnpm run build",
  "run_id": "opencode_dogfood_known_failure_recovery",
  "status": "success",
  "task_type": "validation",
  "tests_status": "passed"
}
```

Follow-up outcome summary:

```json
{
  "count": 3,
  "summary": {
    "memory_effect": {
      "neutral": 3
    },
    "status": {
      "success": 3
    },
    "task_type": {
      "bugfix": 1,
      "refactor": 1,
      "validation": 1
    },
    "tests_status": {
      "passed": 3
    }
  }
}
```

Sandbox audit passed after every follow-up ingest and close. Final audit:

```json
{
  "fixtures_missing": false,
  "negative_failures": [],
  "ok": true,
  "omni_leaks": [],
  "positive_failures": []
}
```

### Non-counted invocation failures

Three setup attempts were abandoned before any transcript was ingested. They are
not counted as dogfood samples:

- one custom provider run failed before transcript creation
- one official APIYI model run failed before transcript creation
- one Windows `Start-Process` invocation passed malformed arguments before
  transcript creation

Each was closed with `task abandon`; none was marked as successful evidence.

## OpenCode real-project controlled cold/warm dogfood

Update: the requested real-project controlled pair was run on 2026-06-16
against a detached qwen-code worktree, not a disposable toy sandbox.

- Real target: `/Users/lijiarui/Downloads/qwen-code-cairn-real-dogfood`
- Source checkout: `/Users/lijiarui/qwen-code-src`
- Target commit: `9ec5bf2a2`
- Package under test: `@qwen-code/acp-bridge`
- Baseline verification: `npm run test --workspace=@qwen-code/acp-bridge`
  passed with 3 files and 44 tests.
- Safety gate: `python3 -m omni.cli audit secrets` returned `ok=true` in the
  target before real dogfood.

The user's dirty source checkout was not edited. The dogfood target was a
separate detached worktree with its own `.omni/` state.

OpenCode's existing global DB failed before launch with `no such column: name`,
so the run used isolated `XDG_DATA_HOME`, `XDG_CACHE_HOME`, and
`XDG_STATE_HOME` paths. The provider config was copied from the local QwenCode
APIYI/DeepSeek provider shape into a temporary OpenCode config under `/tmp`;
API keys stayed in environment variables and no credential was written to the
Cairn Memory repo or the qwen-code target.

### Controlled pair setup

The controlled regression removed `'EPERM'` from
`packages/acp-bridge/src/status.ts`:

```text
npm run test --workspace=@qwen-code/acp-bridge
1 failed | 43 passed
failing test: mapDomainErrorToErrorKind classifies fs ENOENT/EACCES/EPERM as missing_file
```

### Cold bugfix run

Run id: `opencode_real_cold_bugfix`.

Cold conditions:

- no project-local `opencode.json` injection
- no instruction to read Cairn surfaces
- prompt only said to diagnose and fix the acp-bridge failing test

Key observed sequence:

| Seq | Event | Evidence |
|---:|---|---|
| 1 | rediscovery | `Glob packages/acp-bridge/**/*.test.ts` |
| 3 | failed verification | `cd packages/acp-bridge && npx vitest run 2>&1` exited 1 |
| 9 | source search | grep for `mapDomainErrorToErrorKind` |
| 12 | source read | `packages/acp-bridge/src/status.ts` |
| 22 | fix | add `'EPERM'` to `FS_MISSING_CODES` |
| 26 | focused verify | `cd packages/acp-bridge && npx vitest run src/status.test.ts` passed |

The full package verification after the cold repair also passed:

```text
npm run test --workspace=@qwen-code/acp-bridge
3 passed, 44 passed
```

Cold eval before the Phase C eval update:

```json
{
  "run_id": "opencode_real_cold_bugfix",
  "expected_verification_executed": false,
  "rediscovery_count": 1,
  "observed_commands": [
    "npx vitest run 2>&1",
    "npx vitest run src/status.test.ts 2>&1"
  ]
}
```

The cold failed command was then turned into a governed known-failure pattern
through the approved CLI writer path:

```text
python3 -m omni.cli failure extract opencode_real_cold_bugfix
python3 -m omni.cli failure approve failure_cand_f7d56639ea3547c7b43b4c8f5e2c051d \
  --summary "acp-bridge status tests fail when EPERM is omitted from FS_MISSING_CODES." \
  --suggested-action "For this failure, inspect packages/acp-bridge/src/status.ts and restore EPERM in FS_MISSING_CODES, then run the acp-bridge Vitest package tests."
```

The approved pattern id was
`failure_pattern_23325bdf07d344368a3e66721d1ea3ac`.

### Warm bugfix plus known-failure recovery run

Run id: `opencode_real_warm_bugfix`.

Warm conditions:

- `cairn render`
- `cairn inject opencode --mode link`
- the same EPERM regression was reintroduced
- an open bugfix task existed before ingest
- prompt required OpenCode to call the four read-only Cairn surfaces before
  source inspection

Key observed sequence:

| Seq | Event | Evidence |
|---:|---|---|
| 2 | read surface | `python3 -m omni.cli memory read` |
| 3 | read surface | `python3 -m omni.cli failure read` |
| 4 | read surface | `python3 -m omni.cli verify plan --task bugfix` |
| 5 | read surface | `python3 -m omni.cli task read` |
| 6 | known-failure content | `failure read` returned the EPERM recovery action |
| 14 | first source read | `packages/acp-bridge/src/status.ts` |
| 15 | agent rationale | "Cairn surfaces are clear: EPERM is missing..." |
| 22 | fix | add `'EPERM'` to `FS_MISSING_CODES` |
| 28 | verification | `cd packages/acp-bridge && npx vitest run` passed |

External verification after the warm repair:

```text
npm run test --workspace=@qwen-code/acp-bridge
3 passed, 44 passed
```

The warm run was ingested and marked through approved writers:

```text
python3 -m omni.cli ingest opencode_real_warm_bugfix --engine opencode --transcript .dogfood-evidence/opencode-warm-bugfix.jsonl
python3 -m omni.cli outcome mark opencode_real_warm_bugfix --success --tests-passed --memory-effect helped --task-type bugfix
python3 -m omni.cli task close --success
```

### Controlled pair result

This dogfood run exposed a real Phase C evaluation gap: the old behavior eval
recognized `CLAUDE.md` and `.omni/generated/memory.md` reads but did not
recognize the approved C-4 machine-read surfaces. The evaluator now records:

- `machine_read_surfaces`
- `machine_read_context_seen`
- `memory_context_seen`
- `machine_read_adopted`

The resulting read-only dogfood comparison is now reproducible:

```text
python3 -m omni.cli dogfood --warm opencode_real_warm_bugfix --cold opencode_real_cold_bugfix
```

Key result:

```json
{
  "cold_rediscovery_count": 1,
  "warm_rediscovery_count": 0,
  "machine_read_adopted": true,
  "memory_context_adopted": true,
  "warm_machine_read_surfaces": [
    "memory_read",
    "failure_read",
    "verify_plan",
    "task_read"
  ],
  "improvement": true,
  "summary": "warm used machine-read surfaces and reduced rediscovery"
}
```

This closes the earlier "real project + controlled cold/warm" gap for one
OpenCode bugfix and known-failure recovery pair. It does not claim broad
statistical causality across many repositories.

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
| `python -m pytest tests/test_cli_smoke.py tests/test_db.py tests/test_task.py -q` | 134 passed |
| `pytest -q` | 634 passed |
| `git diff --check` | pass |
| `python -m omni.cli audit secrets` | ok=true |

Machine-readable gate anchors:

- `npx -y opencode-ai@latest --version`: 1.17.7
- `python -m pytest tests/test_docs.py -q`: 14 passed
- `python -m pytest tests/test_cli_smoke.py tests/test_db.py tests/test_task.py -q`: 134 passed
- `pytest -q`: 634 passed
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
- OpenCode multi-sample dogfood: five bounded samples across validation,
  release-build validation, bugfix, refactor, and known-failure recovery.
- OpenCode real-project controlled cold/warm dogfood: one detached qwen-code
  bugfix plus known-failure recovery pair with `improvement=true`.
- Behavior eval recognizes Phase C machine-read surfaces (`memory_read`,
  `failure_read`, `verify_plan`, `task_read`) as memory context.
- Safety gates: sandbox `python -m omni.cli audit secrets` passed after the
  OpenCode ingest and close steps.

This evidence is stronger than the original single C-2 sample because it covers
five sandbox OpenCode runs, two verification profiles, task-aware
bugfix/refactor selection, a non-empty known-failure recovery path, and one
real-project controlled cold/warm pair. It still does not prove broad behavior
improvement across many OpenCode task families or repositories.

## Remaining caveats after expanded dogfood

- OpenCode v0 is now proved for bounded validation/build, bugfix, refactor, and
  known-failure recovery prompts in disposable sandboxes, plus one real
  qwen-code controlled cold/warm pair. This is still not broad causal proof
  across many projects and does not prove broad behavioral improvement.
- Failure read is now proved both as a non-empty machine surface and as input to
  successful sandbox and real-project recovery runs.
- The real pair uses one package-local Vitest workflow; `eval run` still reports
  the single warm run as `unknown` because the active expected command facts are
  coarse project commands. The pairwise dogfood metric is the stronger result
  for this task.
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

1. Repeat the controlled OpenCode cold/warm pack on a second real repository to
   test whether the qwen-code result generalizes.
2. Teach verify planning about package-local workspace commands before claiming
   single-run `memory_effect=helped` for monorepo subpackage tasks.
3. Keep the next adapter work at the same boundary: read governed Cairn Memory
   state, capture only redacted transcripts, and write only through human-gated
   Cairn CLI commands.
