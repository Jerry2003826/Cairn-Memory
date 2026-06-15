# CLI-only Claude Code v1 — G6 Robust Sandbox Evidence

Date: 2026-06-15

## What this records

This is corroborating harness evidence that the Week-1 Definition of Done G6
criterion ("a warm run satisfies the robust criterion on 3 of 3 golden tasks")
is achievable end to end on the current build.

Per `AGENTS.md`, the authoritative Week-1 acceptance remains the manual
`docs/demo.md` runbook; `golden_demo` style harness runs are optional coverage.
This record is the automated harness variant, not a replacement for the manual
authoritative pass.

## G6 robust criterion (from docs/demo.md)

A warm run passes robust acceptance when:

- the first command that tries to run tests equals the injected test command, and
- no forbidden rediscovery event occurred before it.

## Method (Windows adaptation)

`scripts/golden_demo.sh` is Bash and `bash` is unavailable on this host, so the
loop was reproduced with PowerShell plus Cairn Memory's own read-only evaluator
instead of the Bash harness:

- disposable sandbox created with `scripts/create_sandbox.ps1` (under TEMP,
  outside the Cairn Memory checkout)
- Claude Code driven headlessly:
  `claude --print --no-session-persistence --session-id <uuid> --permission-mode bypassPermissions --output-format text "<task>"`
- one cold run, then `omni ingest`, `omni render --diff`, `omni render`,
  `omni inject claude --mode link`
- three warm runs, each followed by `omni ingest`
- each warm run judged with `omni eval run <run_id>` (authoritative; includes the
  leading `cd ... &&` command normalization added in PR #43)
- cold/warm compared with `omni eval dogfood`

Environment: `claude` 2.1.173, `node` v22.22.0, `pnpm` 10.33.0.

No product code, tables, or memory types were added. Only the existing CLI was
exercised in a disposable sandbox.

## Sandbox

```
%TEMP%\omni-g6-8091fd02
```

Injected test command in `.omni/generated/memory.md`:

```
- Use pnpm run test for Node tests.
```

## Cold run

- run_id: `cbce3b6c-98f4-4a46-997f-204fe07c5014`
- cold executed `node test.js` directly (rediscovery_count=5); render still
  extracted `pnpm run test` into generated memory.

## Warm runs (source: `omni eval run`)

| # | run_id | expected_verification_executed | first_expected_command | position | rediscovery_count | rediscovery_before_first_expected | memory_effect | robust |
|---|--------|--------------------------------|------------------------|----------|-------------------|-----------------------------------|---------------|--------|
| 1 | `7c5576a2-df52-4f13-ab2c-19c044f5c6ae` | true | `pnpm run test` | 1 | 0 | `[]` | neutral | PASS |
| 2 | `84be53fb-3836-442c-ae68-a8a4fe8bcfec` | true | `pnpm run test` | 1 | 0 | `[]` | neutral | PASS |
| 3 | `b6eb4a35-80f5-4370-b4b5-3e24cd63cf0f` | true | `pnpm run test` | 1 | 0 | `[]` | neutral | PASS |

G6 robust: 3/3.

## Dogfood comparison (source: `omni eval dogfood`, each warm vs cold)

| warm | improvement | command_adopted | cold_rediscovery_count | warm_rediscovery_count |
|------|-------------|-----------------|------------------------|------------------------|
| 1 | true | true | 5 | 0 |
| 2 | true | true | 5 | 0 |
| 3 | true | true | 5 | 0 |

## Safety and verify

- `omni audit secrets`: `ok=true` (no `omni_leaks`, no positive or negative
  failures) after the runs.
- `omni verify`: selected `pnpm run test`, `reason_code=passed`, `status=passed`.

## Notes

- Single-run `memory_effect` stayed `neutral` because no explicit `CLAUDE.md` or
  `.omni/generated/memory.md` `Read` event was observed
  (`memory_md_read=false`, `claude_md_read=false`). This matches the prior
  CLI-only v1 closeout: the cold/warm comparison is the stronger behavior metric.
  All three warm runs still executed the injected command as the first Bash
  action with zero pre-command rediscovery.
- This is sandbox harness evidence. The authoritative manual acceptance path is
  still `docs/demo.md`.
