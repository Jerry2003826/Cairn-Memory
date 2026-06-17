# Cairn Memory Phase C Final Delivery Evidence

Date: 2026-06-16 local, with CLI timestamps recorded in UTC.

Update: after this OpenCode/task closeout, C-4 was approved and landed as
`cairn mcp serve`, a read-only stdio MCP wrapper exposing `memory_read`,
`failure_read`, `verify_plan`, and `task_read`. The historical evidence below
still describes the earlier OpenCode/task delivery state.

Update 2026-06-17: QwenCode v0 was approved and landed after the OpenCode
closeout. It adds only project-local `QWEN.md` managed-region injection and
UTF-8 `qwen --output-format stream-json` transcript ingest through
`cairn ingest --engine qwen --transcript`; it adds no QwenCode background
capture, no global `~/.qwen` edits, no write-capable external surface, and no
new migration. See [`qwen-code-v0-adapter-2026-06-17.md`](qwen-code-v0-adapter-2026-06-17.md).

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

At the time of this closeout, no write-capable MCP server, HTTP transport, or
external write path had been added. OpenCode plugin background capture,
multi-agent router, permission-tier system, UI, vector search, and LLM
extractors were not added.

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

## Package-local verify planning

Update: after the first real qwen-code pair, `verify plan` was taught to keep
workspace package commands as project facts with package-local subjects instead
of flattening all verification commands into the root subject.

The extractor now reads root `package.json` workspace definitions and emits
package commands like this:

```json
{
  "subject": "packages/acp-bridge",
  "qualifier": "node:@qwen-code/acp-bridge",
  "command": "npm run test --workspace=@qwen-code/acp-bridge"
}
```

The qwen-code target was re-ingested after this change. `cairn verify plan
--task bugfix` then listed the package-local acp-bridge command alongside other
workspace commands instead of only root-level commands. This directly closes the
previous caveat that the qwen-code warm run's single-run eval could not see the
expected package-local verification command.

Focused repository tests for this change:

```text
tests/test_extract_scripts.py
tests/test_verify.py
tests/test_machine_read.py
tests/test_mcp.py
tests/test_eval.py
139 passed
```

## OpenCode local repair

Update: the local OpenCode install was also repaired so future dogfood runs do
not need isolated `XDG_*` state just to bypass a stale global database.

- `opencode --version`: `1.17.7`
- Old DB error reproduced: `opencode db path` failed with `no such column: name`
- Old DB files were moved to
  `/Users/lijiarui/.local/share/opencode/db-backup-20260616-220809`
- New `opencode db path` returned
  `/Users/lijiarui/.local/share/opencode/opencode.db`
- Global OpenCode config was backed up to
  `/Users/lijiarui/.config/opencode/opencode.json.backup-20260616-221858`
- Global config now uses the local QwenCode provider shape translated into
  OpenCode providers for `qwen-apiyi/glm-5.1`
- Headless smoke result with the global config: `global-config-smoke-ok`

No provider key is printed in this document, and no credential was written to
the Cairn Memory repository.

## OpenCode second real-project controlled cold/warm dogfood

Update: the "repeat on a second real repository" next step was completed on
2026-06-16 against a detached Cairn Memory worktree. This was intentionally not
another toy sandbox.

- Real target: `/Users/lijiarui/Downloads/Cairn-Memory-real-dogfood-2`
- Source commit: `387ae64`
- Safety gate: `python3 -m omni.cli audit secrets` returned `ok=true`
- Controlled regression: `TASK_QUALIFIER_HINTS["bugfix"]` in
  `src/omni/verify/selection.py` was changed from `node:unit` to `node:e2e`
- Failing focused test before repair:
  `tests/test_verify.py::test_verify_preflight_task_bugfix_maps_to_node_unit_qualifier`

### Second real cold run

Run id: `opencode_cairn_self_cold_bugfix`.

Cold conditions:

- no Cairn read-surface instruction in the prompt
- no project-local `opencode.json` injection
- prompt only said the checkout had one failing focused verify-selection test

Cold ingest:

```text
run_ids=opencode_cairn_self_cold_bugfix events_inserted=14 queue_drained=0
```

The cold run eventually fixed the bug and confirmed:

```text
2 passed in 0.17s
```

But it first rediscovered test environment details: `pytest` was missing,
`pip` was missing, `python3 -m pytest` had no pytest, and it created a temporary
virtualenv before finding and running the focused tests.

The cold transcript then seeded a governed known-failure pattern through the
approved writer path:

```text
python3 -m omni.cli failure extract opencode_cairn_self_cold_bugfix
python3 -m omni.cli failure approve failure_cand_42c8609aaab14219a63605671d2aeea3 \
  --summary "Cairn verify-selection bugfix recovery: a focused verify task can fail when TASK_QUALIFIER_HINTS maps bugfix to node:e2e instead of node:unit." \
  --suggested-action "Inspect src/omni/verify/selection.py and restore TASK_QUALIFIER_HINTS[\"bugfix\"] to \"node:unit\". Then run tests/test_verify.py::test_verify_preflight_task_bugfix_maps_to_node_unit_qualifier and tests/test_verify.py::test_cli_verify_accepts_task_and_profile."
```

### Second real warm run

Run id: `opencode_cairn_self_warm_bugfix`.

Warm conditions:

- `cairn render`
- `cairn inject opencode --mode link`
- the same `node:e2e` regression was reintroduced
- an open bugfix task existed before ingest
- the prompt required OpenCode to call the four read-only Cairn surfaces before
  source inspection

Key observed sequence:

| Seq | Event | Evidence |
|---:|---|---|
| 1 | read surface | `PYTHONPATH=src python3 -m omni.cli memory read` |
| 2 | read surface | `PYTHONPATH=src python3 -m omni.cli failure read` |
| 3 | read surface | `PYTHONPATH=src python3 -m omni.cli verify plan --task bugfix` |
| 4 | read surface | `PYTHONPATH=src python3 -m omni.cli task read` |
| 6 | known-failure content | `failure read` returned the `node:e2e` to `node:unit` recovery action |
| 7 | source read | `src/omni/verify/selection.py` |
| 11 | focused failing tests | two verify-selection tests failed |
| 12 | agent rationale | "machine-read surfaces all confirmed this" |
| 13 | fix | restore `TASK_QUALIFIER_HINTS["bugfix"]` to `node:unit` |
| 15 | verification | two focused tests passed |

Warm ingest:

```text
run_ids=opencode_cairn_self_warm_bugfix events_inserted=13 queue_drained=0
```

Warm eval:

```json
{
  "machine_read_context_seen": true,
  "machine_read_surfaces": [
    "memory_read",
    "failure_read",
    "verify_plan",
    "task_read"
  ],
  "memory_effect": "helped",
  "expected_verification_executed": true,
  "first_expected_command_position": 5
}
```

Pairwise dogfood result:

```json
{
  "cold_comparable": true,
  "command_adopted": true,
  "improvement": true,
  "machine_read_adopted": true,
  "memory_context_adopted": true,
  "warm_machine_read_surfaces": [
    "memory_read",
    "failure_read",
    "verify_plan",
    "task_read"
  ],
  "warm_rediscovery_count": 0
}
```

Outcome and task close were recorded through approved writers:

```text
python3 -m omni.cli outcome mark opencode_cairn_self_warm_bugfix --success --tests-passed --memory-effect helped --task-type bugfix
python3 -m omni.cli task close --success
```

## MCP client acceptance harness

Update: the read-only MCP wrapper is now checked by a real stdio client harness,
not only direct server-function tests or static stdin smoke tests.

Harness:

```text
scripts/mcp_client_acceptance.py
```

The harness starts `python -m omni.cli mcp serve`, sends `initialize`, sends
`notifications/initialized`, calls `tools/list`, verifies the exact read-only
tool list, then calls every tool through `tools/call`:

```json
[
  "memory_read",
  "failure_read",
  "verify_plan",
  "task_read"
]
```

Manual acceptance command against a temporary Cairn project:

```text
python scripts/mcp_client_acceptance.py --root <initialized-project>
```

Observed acceptance result:

```json
{
  "ok": true,
  "tools": [
    "memory_read",
    "failure_read",
    "verify_plan",
    "task_read"
  ]
}
```

The harness asserts that every tool returns a non-error `tools/call` result with
`structuredContent`. It does not add any write-capable MCP tool, HTTP transport,
new migration, or SDK dependency.

## OpenCode additional real-project controlled cold/warm samples

Update: the requested "more real projects / more task families" dogfood pack
was run on 2026-06-17. This adds three more detached real-repo cold/warm pairs
on top of the qwen-code and Cairn Memory pairs above.

Shared controls:

- The original user worktrees were not edited. Each run used a detached
  worktree with project-local `.omni/` state.
- `python3 -m omni.cli audit secrets` returned `ok=true` in Cairn Memory and
  in every target before real-project dogfood.
- Cold runs had no instruction to read Cairn surfaces.
- Warm runs called the four read-only surfaces before source inspection:
  `memory read`, `failure read`, `verify plan`, and `task read`.
- Each cold transcript seeded one reviewed known-failure pattern through
  `failure extract` and `failure approve`; each warm run then recovered the same
  injected regression from that read surface.

| Target | Source commit | Task family | Verification | Cold run | Warm run | Pattern |
|---|---|---|---|---|---|---|
| `cardgame3077` | `0dae7d3` | Python scoring bugfix | `python3 -m unittest tests.test_scoring` | `opencode_cardgame_cold_bugfix` | `opencode_cardgame_warm_bugfix` | `failure_pattern_6c65f86202554e3298c868b8348be4a1` |
| `lite-cv-ai` | `8321bf7` | Vite release-build recovery | `npm run build` | `opencode_lite_cv_cold_build` | `opencode_lite_cv_warm_build` | `failure_pattern_d8998fe3f6554242b05137a07ba6265a` |
| `cakephp-app` | `4aad785` | CakePHP backend bugfix | `vendor/bin/phpunit --colors=never tests/TestCase/Service/StripeCheckoutSessionClassifierTest.php` | `opencode_cakephp_cold_bugfix` | `opencode_cakephp_warm_bugfix` | `failure_pattern_690718700e26464aafbdb5b31640e166` |

### Additional pair 1: cardgame3077 scoring bugfix

Real target: `/Users/lijiarui/Downloads/cardgame3077-cairn-dogfood`.

Baseline:

```text
python3 -m unittest tests.test_scoring
Ran 7 tests in 0.019s
OK
```

Controlled regression: completed destination tickets in
`app/services/scoring_service.py` subtracted `ticket.points` instead of adding
them. The failing check produced two scoring failures, including
`AssertionError: -6 != 6`.

Cold observed sequence:

- ran `python3 -m unittest tests.test_scoring`
- read `tests/test_scoring.py`
- globbed for `**/*scoring*.py`
- read `app/services/scoring_service.py`
- changed `ticket_delta -= ticket.points` to `ticket_delta += ticket.points`
- reran `python3 -m unittest tests.test_scoring`, which passed 7 tests

Warm observed sequence:

- `memory read` returned the reviewed scoring known-failure item
- `failure read` returned the suggested action to inspect
  `app/services/scoring_service.py` and restore completed-ticket addition
- `verify plan --task bugfix` returned a read-only plan response
- `task read` returned the open bugfix task
- the agent then read `app/services/scoring_service.py`, applied the one-line
  fix, and reran `python3 -m unittest tests.test_scoring`

Pairwise result:

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
  "improvement": true
}
```

### Additional pair 2: lite-cv-ai release-build recovery

Real target: `/Users/lijiarui/Downloads/lite-cv-ai-cairn-dogfood`.

Baseline:

```text
npm run build
vite v7.3.5 building client environment for production...
Prerendered 1 page:
  /
```

Controlled regression: `src/shared/markdown.tsx` changed
`export default function Markdown` to `export function Markdown`, while nine
theme files still used default imports. The failing build emitted `TS2613`
errors for the missing default export.

Cold observed sequence:

- ran `ls -la`
- ran `npm run build`, which failed with `TS2613`
- read `src/shared/markdown.tsx`
- restored `export default function Markdown`
- reran `npm run build`, which passed

Warm observed sequence:

- `memory read` and `failure read` returned the reviewed Markdown default-export
  recovery action
- `verify plan --profile release` returned a read-only release predicate
- `task read` returned the open validation task
- the agent stated that the Cairn surfaces identified
  `src/shared/markdown.tsx`, restored the default export, and reran
  `npm run build`

Pairwise result:

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
  "improvement": true
}
```

### Additional pair 3: cakephp-app backend classifier bugfix

Real target: `/Users/lijiarui/Downloads/cakephp-app-cairn-dogfood`.

Baseline:

```text
vendor/bin/phpunit --colors=never tests/TestCase/Service/StripeCheckoutSessionClassifierTest.php
OK (6 tests, 6 assertions)
```

Controlled regression: `src/Service/StripeCheckoutSessionClassifier.php`
returned `STATE_STALE` in the `sessionStatus === 'expired'` branch instead of
`STATE_EXPIRED`. The focused PHPUnit test failed with expected `expired` and
actual `stale`.

Cold observed sequence:

- ran the focused PHPUnit command and got one failure
- read the PHPUnit test
- globbed `src/Service/StripeCheckoutSessionClassifier*`
- read `src/Service/StripeCheckoutSessionClassifier.php`
- changed the expired branch from `STATE_STALE` to `STATE_EXPIRED`
- reran the focused PHPUnit command, which passed 6 tests

Warm observed sequence:

- `memory read` and `failure read` returned the reviewed expired-session
  classifier recovery action
- `verify plan --task bugfix` returned a read-only plan response
- `task read` returned the open bugfix task
- the agent stated that Cairn surfaces confirmed the exact expired-branch bug,
  read the service class, restored `STATE_EXPIRED`, and reran the focused
  PHPUnit command

Pairwise result:

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
  "improvement": true
}
```

This raises the delivery from two to five real-project controlled cold/warm
pairs across five repositories: qwen-code, Cairn Memory, cardgame3077,
lite-cv-ai, and cakephp-app. It is materially stronger than the earlier state,
but it still should not be described as broad statistical proof.

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
| `pytest -q` | 638 passed |
| `git diff --check` | pass |
| `python -m omni.cli audit secrets` | ok=true |

Machine-readable gate anchors:

- `npx -y opencode-ai@latest --version`: 1.17.7
- `python -m pytest tests/test_docs.py -q`: 14 passed
- `python -m pytest tests/test_cli_smoke.py tests/test_db.py tests/test_task.py -q`: 134 passed
- `pytest -q`: 638 passed
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
- OpenCode second real-project controlled cold/warm dogfood: one detached Cairn
  Memory self-dogfood bugfix pair with `memory_effect=helped` and
  `improvement=true`.
- OpenCode additional real-project controlled cold/warm samples: three detached
  real-repo pairs across Python scoring, Vite release-build recovery, and
  CakePHP backend bugfix tasks, each with `improvement=true`.
- Package-local workspace verify planning: monorepo package commands now retain
  package subjects and are visible to `verify plan`.
- MCP client acceptance harness: a real stdio client launches `cairn mcp serve`,
  lists tools, and calls `memory_read`, `failure_read`, `verify_plan`, and
  `task_read`.
- Behavior eval recognizes Phase C machine-read surfaces (`memory_read`,
  `failure_read`, `verify_plan`, `task_read`) as memory context.
- Safety gates: sandbox `python -m omni.cli audit secrets` passed after the
  OpenCode ingest and close steps.

This evidence is stronger than the original single C-2 sample because it covers
five sandbox OpenCode runs, two verification profiles, task-aware
bugfix/refactor selection, a non-empty known-failure recovery path,
package-local verify planning, and five real controlled pairs.

The delivery now includes five real-project controlled cold/warm pairs. It is
no longer just "directionally plausible from two repos"; it still does not
prove broad behavior improvement across many OpenCode task families or
repositories.

## Remaining caveats after expanded dogfood

- OpenCode v0 is now proved for bounded validation/build, bugfix, refactor, and
  known-failure recovery prompts in disposable sandboxes, plus five real
  controlled cold/warm pairs. This is still not broad causal proof across many
  projects and does not prove broad behavioral improvement.
- Failure read is now proved both as a non-empty machine surface and as input to
  successful sandbox and real-project recovery runs.
- The qwen-code real pair now has package-local verify planning support, but it
  remains one package-local Vitest workflow rather than broad monorepo coverage.
- The task lifecycle is implemented for a single open task; multi-agent handoff
  remains outside this approved slice.

## Explicitly not implemented at this closeout

- No write-capable MCP server or HTTP transport; C-4 landed only as a read-only stdio wrapper over existing read surfaces.
- No external write path for OpenCode, Codex, QwenCode, Cursor, or any other
  agent.
- No OpenCode background plugin or automatic capture loop.
- No multi-engine router or replacement coding agent.
- No permission-tier product surface.
- No UI, dashboard, TUI, or team account system.
- No vector or embedding search.
- No LLM extractor or automatic memory evolution.

## Next smallest high-value tasks

1. Add a small aggregate report command or script for summarizing accumulated
   cold/warm pairs, so future samples do not require hand-copying dogfood JSON
   into closeout notes.
2. Run the MCP client acceptance harness against one external MCP-capable agent
   configuration after choosing that agent's approved local config path.
3. Keep the next adapter work at the same boundary: read governed Cairn Memory
   state, capture only redacted transcripts, and write only through human-gated
   Cairn CLI commands.
