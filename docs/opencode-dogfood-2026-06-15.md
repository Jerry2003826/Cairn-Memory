# OpenCode Dogfood Evidence - 2026-06-15

Date: 2026-06-15

Scope: Phase C productization evidence. This is a real OpenCode run using the
approved read-only OmniAgent CLI surfaces. It is **not** a C-2 OpenCode capture
adapter, not MCP, and not an external write path.

## Boundary

OpenCode remained the coding-agent runtime. OmniAgent only provided governed
brain-layer state:

- reviewed local memory through `omni memory read`
- reviewed failure memory through `omni failure read`
- verification selection through `omni verify plan`
- task context through `omni task read`
- run, task, and outcome evidence through the existing human-invoked approved
  CLI writers

No OpenCode adapter, MCP server, multi-agent handoff, permission tier, UI, vector
search, LLM extractor, or automatic memory evolution was implemented.

## Environment

- OmniAgent checkout: `C:\Users\Jiarui Li\Documents\OmniAgent`
- Sandbox: `C:\Users\Jiarui Li\AppData\Local\Temp\omniagent-opencode-dogfood-20260615-141758`
- OpenCode invocation: `npx -y opencode-ai@latest run --format json --model apiyi/qwen3.7-max --agent build --dangerously-skip-permissions`
- Provider config: sandbox-local `opencode.json`, with API key read from an
  environment variable. No key was written to the repo or printed in this
  record.

## Preconditions

The sandbox was created with `scripts/create_sandbox.ps1`, then initialized with
OmniAgent:

```powershell
python -m omni.cli init
python -m omni.cli audit secrets
python -m omni.cli ingest bootstrap_static
python -m omni.cli render
```

The sandbox audit passed after setup and again after the OpenCode dogfood run:

```json
{
  "fixtures_missing": false,
  "negative_failures": [],
  "ok": true,
  "omni_leaks": [],
  "positive_failures": []
}
```

## Seeded Read Surfaces

`omni memory read` exposed command and project facts:

```json
{
  "schema_version": 1,
  "sections": [
    {
      "items": [
        "- Use pnpm run test for Node tests.",
        "- Use pnpm run build to build Node."
      ],
      "kind": "Commands"
    },
    {
      "items": [
        "- If `pnpm run build` fails with `dependency resolution failed while reading lockfile`: Inspect pnpm-lock.yaml before changing package managers."
      ],
      "kind": "Known Failures"
    },
    {
      "items": [
        "- node package manager: pnpm"
      ],
      "kind": "Project"
    }
  ]
}
```

`omni failure read` exposed the approved known failure:

```json
[
  {
    "command_norm": "pnpm run build",
    "suggested_action": "Inspect pnpm-lock.yaml before changing package managers.",
    "summary": "Build can fail when dependency resolution fails."
  }
]
```

`omni verify plan` selected the verification command without executing it:

```json
{
  "candidate_commands": [
    {
      "command": "pnpm run test",
      "qualifier": "node"
    }
  ],
  "predicate": "uses_test_command",
  "profile": null,
  "qualifier": null,
  "schema_version": 1,
  "selection_mode": "auto"
}
```

`omni task read` showed the open validation task to OpenCode without ids,
timestamps, or evidence metadata:

```json
{
  "schema_version": 1,
  "tasks": [
    {
      "run_count": 0,
      "status": "open",
      "task_type": "validation",
      "title": "OpenCode validates sandbox using OmniAgent read surfaces"
    }
  ]
}
```

## OpenCode Run Evidence

OpenCode was instructed not to inspect project source files and to use the
OmniAgent read surfaces before running the selected verification command.

The resulting OpenCode transcript contained these tool-use events:

| Seq | Command | Exit |
|---:|---|---:|
| 2 | `python -m omni.cli memory read` | 0 |
| 5 | `python -m omni.cli failure read` | 0 |
| 8 | `python -m omni.cli verify plan` | 0 |
| 11 | `python -m omni.cli task read` | 0 |
| 14 | `pnpm run test` | 0 |

The final test output was:

```text
sandbox test ok
```

OpenCode's final response stated that it read all four OmniAgent surfaces,
selected `pnpm run test`, passed verification, and performed no rediscovery file
reads before the command. The command list above is the stronger evidence: the
only executed shell commands before the test were OmniAgent read surfaces.

## Ledger Evidence

The OpenCode transcript was ingested as run `opencode_dogfood_run`.

PowerShell `Tee-Object` first wrote a UTF-16LE JSONL file, which OmniAgent
handled safely as archive-only input (`events_inserted=0`). The same transcript
was then converted to UTF-8 and ingested again, yielding 18 normalized events.
This records a useful C-2 fact: a future OpenCode adapter should treat transcript
encoding explicitly instead of guessing.

The open task was then closed through the approved CLI writer:

```powershell
python -m omni.cli task close --success --from-verify
```

Task evidence:

```json
{
  "attached_run_count": 1,
  "evidence": {
    "run_count": 1,
    "source": "task_close",
    "verify_reason_code": "passed"
  },
  "outcome_status": "success",
  "status": "closed",
  "task_id": "task_1244eecbc49440a0a410deffe676a3bc",
  "task_type": "validation",
  "tests_status": "passed",
  "title": "OpenCode validates sandbox using OmniAgent read surfaces"
}
```

Outcome ledger evidence:

```json
{
  "final_command": "pnpm run test",
  "outcome_id": "outcome_1731696b9ff74fa78b92840cc97c2d45",
  "run_id": "opencode_dogfood_run",
  "status": "success",
  "task_type": "validation",
  "tests_status": "passed",
  "verify": {
    "command": "pnpm run test",
    "exit_code": 0,
    "reason_code": "passed",
    "selection_mode": "task",
    "selection_reason": "selected active uses_test_command fact"
  }
}
```

## Conclusion

This constrained run proves the current Phase C governed brain layer can be
consumed by a real non-Claude agent through read-only CLI surfaces, then leave
run, task, and outcome evidence through the existing approved write path. In
this transcript, OpenCode ran the selected verification command without separate
shell-level rediscovery file reads before the test. It does not prove baseline
behavior improvement without more cold/warm OpenCode samples.

It does not prove the full C-2 adapter. That remains the next governed
integration step: capture OpenCode output through a redacted append-only seam,
record the observed schema and encoding behavior, and keep all DB writes behind
the existing CLI writer path.
