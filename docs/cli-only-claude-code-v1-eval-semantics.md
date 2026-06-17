# CLI-only Claude Code v1 — Behavior Eval Semantics

`cairn eval run <run_id>` and `cairn eval dogfood` classify whether an ingested run
appears to use memory effectively. Both are **read-only** (they open SQLite
read-only and run no migrations) and **heuristic** — a single result is evidence,
not causal proof. This document explains the output fields and the
`memory_effect` rules, aligned to `src/omni/eval/classify.py`.

## `cairn eval run`

| field | meaning |
|---|---|
| `claude_md_read` / `qwen_md_read` / `opencode_config_read` / `memory_md_read` | a project context reference was observed through `CLAUDE.md`, `QWEN.md`, `opencode.json`, or `.omni/generated/memory.md` |
| `machine_read_surfaces` / `machine_read_context_seen` | read-only machine surfaces such as `cairn memory read`, `cairn failure read`, `cairn verify plan`, or `cairn task read` were called |
| `memory_context_seen` | any supported memory context signal was observed: Claude/Qwen/OpenCode injection, generated memory, or machine-read surface |
| `active_expected_commands` | active facts grouped by predicate (`uses_test_command`, `uses_build_command`, `uses_lint_command`, `uses_typecheck_command`) |
| `observed_commands` | the command sequence observed in the run (bounded, redacted) |
| `first_expected_command` / `first_expected_command_position` | the first observed command that matched an expected command, and its event `seq` |
| `rediscovery_count` / `rediscovery_events_before_first_expected_command` | rediscovery observed **before** the first expected command |
| `expected_verification_executed` | whether any expected command was executed |
| `memory_context_seen_but_no_expected_command` | memory context appeared but no expected command ran |
| `memory_effect` / `reason` | the heuristic classification and its explanation |

### What counts as rediscovery

Rediscovery is work that re-derives what memory already knows, counted only
*before* the first expected command:

- reads/refs of `README.md`, `package.json`, `pnpm-lock.yaml`,
  `package-lock.json`, `yarn.lock`, `DEPLOY.md`
- broad scans: `Glob`, `LS`, `Get-ChildItem`, `rg --files`, `find .`, `tree`,
  bare `ls` / `dir`

A leading `cd` / `chdir` / `pushd <dir> &&` prefix is stripped before matching,
so `cd "<project>" && pnpm run test` is recognized as `pnpm run test`. Package
manager forms are canonicalized, so `pnpm test` matches an expected
`pnpm run test`.

## `memory_effect` rules

| `memory_effect` | when |
|---|---|
| `helped` | an expected command ran with `rediscovery_count == 0` **and** memory context was observed through a supported injection file, generated memory, or machine-read surface |
| `neutral` | an expected command ran before rediscovery but **no** memory context was observed; or an expected command ran **after** rediscovery |
| `failed_to_help` | memory context was observed and rediscovery occurred, but **no** expected command ran |
| `unknown` | no active expected facts or no events; or memory context appeared with neither an expected command nor rediscovery; or evidence is otherwise insufficient |

Key rule: without observable memory-context evidence, a clean run is classified
`neutral`, never `helped`. Some agents may import their context file without
emitting a detectable `Read` event, so `neutral` is expected even when behavior
is good — which is why the cold/warm comparison below is the stronger signal.

## `cairn eval dogfood`

Compares a cold (or older) run against a warm run.

| field | meaning |
|---|---|
| `cold_comparable` | the cold run exists and has events |
| `cold_rediscovery_count` / `warm_rediscovery_count` | rediscovery before the first expected command, per run |
| `cold_first_expected_command_position` / `warm_first_expected_command_position` | event `seq` of the first expected command, per run |
| `command_adopted` | cold ran no expected command but warm did |
| `machine_read_adopted` / `warm_machine_read_surfaces` | the warm run used read-only machine surfaces that the cold run did not |
| `improvement` | `true` when the cold run is comparable, the warm run executed an expected command, **and** (command was adopted, or rediscovery decreased, or the expected command moved earlier) |
| `memory_effect_summary` | the per-run `memory_effect` plus a one-line summary |

Treat `improvement` from a cold/warm comparison as stronger evidence than a
single-run `memory_effect`. The recorded reference is
`docs/cli-only-claude-code-v1-closeout-2026-06-15.md` (rediscovery 10 → 0,
`pnpm run test` adopted as the first expected command).

## Boundaries

- Heuristic, not causal proof; a single `memory_effect` is not a verdict.
- Output is redacted and bounded.
- Read-only with respect to Cairn Memory state: no writes, no migrations. Outcomes
  are recorded separately via `cairn outcome mark` / `cairn outcome mark-from-verify`.
